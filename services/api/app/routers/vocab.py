from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import LearnerProfile, SrsState, User, VocabItem
from app.schemas.vocab import (
    VocabAddRequest,
    VocabItemResponse,
    VocabListResponse,
    VocabReviewNextRequest,
    VocabReviewNextResponse,
    VocabReviewSubmitRequest,
    VocabReviewSubmitResponse,
)
from app.services.srs import next_srs_state, utcnow
from app.services.vocab_ai import enrich_vocab_entry
from app.services.local_llm import is_local_llm_enabled
from app.services.openai_key_runtime import get_runtime_openai_key
from app.services.provider_config import get_llm_provider

router = APIRouter(prefix="/vocab", tags=["vocab"])


def _get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user:
        return user
    user = User(id=user_id)
    db.add(user)
    db.flush()
    return user


def _runtime_enrichment_source() -> str:
    provider = get_llm_provider()
    local_available = is_local_llm_enabled()
    has_openai_key = bool(get_runtime_openai_key())
    if provider == "local":
        if local_available:
            return "local"
        if has_openai_key:
            return "openai"
        return "fallback"
    if has_openai_key:
        return "openai"
    if local_available:
        return "local"
    return "fallback"


def _to_item_response(
    item: VocabItem,
    state: SrsState | None,
    *,
    enrichment_source: str | None = None,
) -> VocabItemResponse:
    derived_source = enrichment_source
    if derived_source is None:
        if item.example or item.phonetics:
            derived_source = _runtime_enrichment_source()
        else:
            derived_source = "manual"
    return VocabItemResponse(
        id=item.id,
        user_id=item.user_id,
        word=item.word,
        translation=item.translation,
        example=item.example,
        phonetics=item.phonetics,
        due_at=state.due_at if state else None,
        interval_days=state.interval_days if state else None,
        ease=state.ease if state else None,
        enrichment_source=derived_source,
    )


@router.get("", response_model=VocabListResponse)
def vocab_list(user_id: int, db: Session = Depends(get_db)) -> VocabListResponse:
    items = db.scalars(select(VocabItem).where(VocabItem.user_id == user_id).order_by(VocabItem.id.asc())).all()
    payload = [_to_item_response(item, item.srs_state) for item in items]
    return VocabListResponse(items=payload)


@router.post("/add", response_model=VocabItemResponse)
def vocab_add(payload: VocabAddRequest, db: Session = Depends(get_db)) -> VocabItemResponse:
    _get_or_create_user(db, payload.user_id)
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == payload.user_id))
    target_lang = profile.target_lang if profile is not None else "en"
    native_lang = profile.native_lang if profile is not None else "en"

    final_translation = payload.translation
    final_example = payload.example
    final_phonetics = payload.phonetics
    enrichment_source: str | None = "manual"
    if final_example is None or final_phonetics is None:
        enrichment = enrich_vocab_entry(
            payload.word,
            payload.translation,
            native_lang=native_lang,
            target_lang=target_lang,
        )
        final_translation = enrichment.get("translation") or final_translation
        if final_example is None:
            final_example = enrichment.get("example")
        if final_phonetics is None:
            final_phonetics = enrichment.get("phonetics")
        enrichment_source = enrichment.get("source") or "fallback"

    item = VocabItem(
        user_id=payload.user_id,
        word=payload.word,
        translation=final_translation,
        example=final_example,
        phonetics=final_phonetics,
    )
    db.add(item)
    db.flush()

    state = SrsState(
        vocab_item_id=item.id,
        interval_days=1,
        ease=2.5,
        due_at=datetime.now(UTC),
    )
    db.add(state)
    db.commit()
    db.refresh(item)
    return _to_item_response(item, item.srs_state, enrichment_source=enrichment_source)


@router.post("/review/next", response_model=VocabReviewNextResponse)
def vocab_review_next(payload: VocabReviewNextRequest, db: Session = Depends(get_db)) -> VocabReviewNextResponse:
    now = utcnow()
    row = db.execute(
        select(VocabItem, SrsState)
        .join(SrsState, SrsState.vocab_item_id == VocabItem.id)
        .where(VocabItem.user_id == payload.user_id, SrsState.due_at <= now)
        .order_by(SrsState.due_at.asc())
    ).first()

    if not row:
        return VocabReviewNextResponse(has_item=False, item=None)
    item, state = row
    return VocabReviewNextResponse(has_item=True, item=_to_item_response(item, state))


@router.post("/review/submit", response_model=VocabReviewSubmitResponse)
def vocab_review_submit(
    payload: VocabReviewSubmitRequest,
    db: Session = Depends(get_db),
) -> VocabReviewSubmitResponse:
    item = db.get(VocabItem, payload.vocab_item_id)
    if item is None or item.user_id != payload.user_id:
        raise HTTPException(status_code=404, detail="Vocab item not found")
    state = item.srs_state
    if state is None:
        raise HTTPException(status_code=404, detail="SRS state not found")

    next_state = next_srs_state(
        interval_days=state.interval_days,
        ease=state.ease,
        rating=payload.rating,
    )
    state.interval_days = next_state.interval_days
    state.ease = next_state.ease
    state.last_reviewed_at = utcnow()
    state.due_at = next_state.due_at
    db.commit()

    return VocabReviewSubmitResponse(
        vocab_item_id=item.id,
        rating=payload.rating,
        next_due_at=state.due_at,
        interval_days=state.interval_days,
        ease=state.ease,
    )
