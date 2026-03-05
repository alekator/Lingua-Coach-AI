from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import LearningWorkspace, User

LOCAL_OWNER_USER_ID = 1


def get_or_create_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is not None:
        return user
    user = User(id=user_id)
    db.add(user)
    db.flush()
    return user


def get_or_create_local_owner(db: Session) -> User:
    return get_or_create_user(db, LOCAL_OWNER_USER_ID)


def get_active_workspace(db: Session, owner_user_id: int = LOCAL_OWNER_USER_ID) -> LearningWorkspace | None:
    return db.scalar(
        select(LearningWorkspace)
        .where(
            LearningWorkspace.owner_user_id == owner_user_id,
            LearningWorkspace.is_active.is_(True),
        )
        .order_by(LearningWorkspace.updated_at.desc(), LearningWorkspace.id.desc())
    )


def set_active_workspace(db: Session, workspace: LearningWorkspace) -> None:
    db.query(LearningWorkspace).filter(
        LearningWorkspace.owner_user_id == workspace.owner_user_id,
        LearningWorkspace.id != workspace.id,
    ).update({"is_active": False}, synchronize_session=False)
    workspace.is_active = True


def normalize_lang(lang: str) -> str:
    return lang.strip().lower()


def get_workspace_by_lang_pair(
    db: Session,
    native_lang: str,
    target_lang: str,
    owner_user_id: int = LOCAL_OWNER_USER_ID,
) -> LearningWorkspace | None:
    return db.scalar(
        select(LearningWorkspace).where(
            LearningWorkspace.owner_user_id == owner_user_id,
            LearningWorkspace.native_lang == normalize_lang(native_lang),
            LearningWorkspace.target_lang == normalize_lang(target_lang),
        )
    )


def get_workspace_for_user(
    db: Session,
    learner_user_id: int,
    owner_user_id: int = LOCAL_OWNER_USER_ID,
) -> LearningWorkspace | None:
    return db.scalar(
        select(LearningWorkspace).where(
            LearningWorkspace.owner_user_id == owner_user_id,
            LearningWorkspace.learner_user_id == learner_user_id,
        )
    )


def create_workspace(
    db: Session,
    native_lang: str,
    target_lang: str,
    goal: str | None,
    make_active: bool = True,
    owner_user_id: int = LOCAL_OWNER_USER_ID,
) -> LearningWorkspace:
    owner = get_or_create_user(db, owner_user_id)
    native = normalize_lang(native_lang)
    target = normalize_lang(target_lang)
    existing = get_workspace_by_lang_pair(db, native, target, owner.id)
    if existing is not None:
        existing.goal = goal if goal is not None else existing.goal
        if make_active:
            set_active_workspace(db, existing)
        db.flush()
        return existing

    learner_user = User()
    db.add(learner_user)
    db.flush()

    workspace = LearningWorkspace(
        owner_user_id=owner.id,
        learner_user_id=learner_user.id,
        native_lang=native,
        target_lang=target,
        goal=goal,
        is_active=False,
    )
    db.add(workspace)
    db.flush()
    if make_active or get_active_workspace(db, owner.id) is None:
        set_active_workspace(db, workspace)
    return workspace
