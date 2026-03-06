from __future__ import annotations

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import (
    AIUsageEvent,
    ChatSession,
    Homework,
    HomeworkSubmission,
    LearnerProfile,
    LearningWorkspace,
    Message,
    Mistake,
    PlacementAnswer,
    PlacementSession,
    SessionStepProgress,
    SkillSnapshot,
    SrsState,
    User,
    VocabItem,
)
from app.schemas.app_bootstrap import (
    AppBackupExportResponse,
    AppBackupRestoreRequest,
    AppBackupRestoreResponse,
    AppBootstrapResponse,
    AppResetRequest,
    AppResetResponse,
)
from app.services.reset import reset_local_app_data
from app.services.workspaces import LOCAL_OWNER_USER_ID, get_active_workspace, get_or_create_local_owner

router = APIRouter(prefix="/app", tags=["app"])


MODEL_EXPORT_MAP: dict[str, Any] = {
    "users": User,
    "learning_workspaces": LearningWorkspace,
    "learner_profiles": LearnerProfile,
    "placement_sessions": PlacementSession,
    "placement_answers": PlacementAnswer,
    "sessions": ChatSession,
    "messages": Message,
    "mistakes": Mistake,
    "skill_snapshots": SkillSnapshot,
    "vocab_items": VocabItem,
    "srs_state": SrsState,
    "homeworks": Homework,
    "homework_submissions": HomeworkSubmission,
    "session_step_progress": SessionStepProgress,
    "ai_usage_events": AIUsageEvent,
}
MODEL_RESTORE_ORDER = [
    "users",
    "learning_workspaces",
    "learner_profiles",
    "placement_sessions",
    "placement_answers",
    "sessions",
    "messages",
    "mistakes",
    "skill_snapshots",
    "vocab_items",
    "srs_state",
    "homeworks",
    "homework_submissions",
    "session_step_progress",
    "ai_usage_events",
]


def _serialize_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return value


def _serialize_rows(db: Session, model: Any) -> list[dict[str, Any]]:
    rows = db.query(model).all()
    payload: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for column in model.__table__.columns:
            item[column.name] = _serialize_value(getattr(row, column.name))
        payload.append(item)
    return payload


def _deserialize_value(column: Any, value: Any) -> Any:
    if value is None:
        return None
    python_type = getattr(column.type, "python_type", None)
    if python_type is datetime and isinstance(value, str):
        return datetime.fromisoformat(value)
    if python_type is date and isinstance(value, str):
        return date.fromisoformat(value)
    return value


def _restore_rows(db: Session, model: Any, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    prepared: list[dict[str, Any]] = []
    for row in rows:
        item: dict[str, Any] = {}
        for column in model.__table__.columns:
            if column.name in row:
                item[column.name] = _deserialize_value(column, row[column.name])
        prepared.append(item)
    db.execute(model.__table__.insert(), prepared)
    return len(prepared)


@router.get("/bootstrap", response_model=AppBootstrapResponse)
def app_bootstrap(db: Session = Depends(get_db)) -> AppBootstrapResponse:
    owner = get_or_create_local_owner(db)
    active_workspace = get_active_workspace(db, owner.id)
    active_user_id = active_workspace.learner_user_id if active_workspace else LOCAL_OWNER_USER_ID
    profile = db.scalar(select(LearnerProfile).where(LearnerProfile.user_id == active_user_id))
    has_profile = profile is not None
    needs_onboarding = not has_profile
    next_step = "onboarding" if needs_onboarding else "dashboard"
    db.commit()

    return AppBootstrapResponse(
        user_id=active_user_id,
        has_profile=has_profile,
        needs_onboarding=needs_onboarding,
        next_step=next_step,
        owner_user_id=owner.id,
        active_workspace_id=active_workspace.id if active_workspace else None,
        active_workspace_native_lang=active_workspace.native_lang if active_workspace else None,
        active_workspace_target_lang=active_workspace.target_lang if active_workspace else None,
        active_workspace_goal=active_workspace.goal if active_workspace else None,
    )


@router.post("/reset", response_model=AppResetResponse)
def app_reset(payload: AppResetRequest, db: Session = Depends(get_db)) -> AppResetResponse:
    if payload.confirmation.strip().upper() != "RESET":
        raise HTTPException(status_code=400, detail="Confirmation token must be RESET")
    summary = reset_local_app_data(db)
    return AppResetResponse(
        status="ok",
        deleted_users=int(summary["deleted_users"]),
        deleted_workspaces=int(summary["deleted_workspaces"]),
        deleted_profiles=int(summary["deleted_profiles"]),
        deleted_vocab_items=int(summary["deleted_vocab_items"]),
        deleted_chat_sessions=int(summary["deleted_chat_sessions"]),
        openai_key_cleared=bool(summary["openai_key_cleared"]),
    )


@router.get("/backup/export", response_model=AppBackupExportResponse)
def app_backup_export(db: Session = Depends(get_db)) -> AppBackupExportResponse:
    snapshot: dict[str, Any] = {}
    for table_name, model in MODEL_EXPORT_MAP.items():
        snapshot[table_name] = _serialize_rows(db, model)
    return AppBackupExportResponse(
        version=1,
        exported_at=datetime.utcnow().isoformat(),
        snapshot=snapshot,
    )


@router.post("/backup/restore", response_model=AppBackupRestoreResponse)
def app_backup_restore(payload: AppBackupRestoreRequest, db: Session = Depends(get_db)) -> AppBackupRestoreResponse:
    if payload.confirmation.strip().upper() != "RESTORE":
        raise HTTPException(status_code=400, detail="Confirmation token must be RESTORE")

    reset_local_app_data(db)
    restored_tables: dict[str, int] = {}
    for table_name in MODEL_RESTORE_ORDER:
        model = MODEL_EXPORT_MAP[table_name]
        rows = payload.snapshot.get(table_name, [])
        if not isinstance(rows, list):
            raise HTTPException(status_code=400, detail=f"Snapshot field '{table_name}' must be a list")
        restored_tables[table_name] = _restore_rows(db, model, rows)
    db.commit()
    return AppBackupRestoreResponse(status="ok", restored_tables=restored_tables)
