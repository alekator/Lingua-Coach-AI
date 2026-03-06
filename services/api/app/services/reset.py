from __future__ import annotations

import os

from sqlalchemy.orm import Session

from app.models import (
    AIUsageEvent,
    AppSecret,
    ChatSession,
    GrammarAnalysisRecord,
    Homework,
    HomeworkSubmission,
    LearnerProfile,
    LearningWorkspace,
    Message,
    Mistake,
    PlacementAnswer,
    PlacementSession,
    SkillSnapshot,
    SessionStepProgress,
    SrsState,
    User,
    VocabItem,
)


def reset_local_app_data(db: Session) -> dict[str, int | bool]:
    deleted_messages = db.query(Message).delete(synchronize_session=False)
    deleted_chat_sessions = db.query(ChatSession).delete(synchronize_session=False)
    deleted_placement_answers = db.query(PlacementAnswer).delete(synchronize_session=False)
    deleted_placement_sessions = db.query(PlacementSession).delete(synchronize_session=False)
    deleted_homework_submissions = db.query(HomeworkSubmission).delete(synchronize_session=False)
    deleted_homeworks = db.query(Homework).delete(synchronize_session=False)
    deleted_srs_state = db.query(SrsState).delete(synchronize_session=False)
    deleted_vocab_items = db.query(VocabItem).delete(synchronize_session=False)
    deleted_mistakes = db.query(Mistake).delete(synchronize_session=False)
    deleted_skill_snapshots = db.query(SkillSnapshot).delete(synchronize_session=False)
    deleted_session_step_progress = db.query(SessionStepProgress).delete(synchronize_session=False)
    deleted_ai_usage_events = db.query(AIUsageEvent).delete(synchronize_session=False)
    deleted_grammar_analysis_records = db.query(GrammarAnalysisRecord).delete(synchronize_session=False)
    deleted_app_secrets = db.query(AppSecret).delete(synchronize_session=False)
    deleted_profiles = db.query(LearnerProfile).delete(synchronize_session=False)
    deleted_workspaces = db.query(LearningWorkspace).delete(synchronize_session=False)
    deleted_users = db.query(User).delete(synchronize_session=False)

    openai_key_cleared = False
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
        openai_key_cleared = True
    if deleted_app_secrets:
        openai_key_cleared = True

    db.commit()
    return {
        "deleted_messages": int(deleted_messages or 0),
        "deleted_chat_sessions": int(deleted_chat_sessions or 0),
        "deleted_placement_answers": int(deleted_placement_answers or 0),
        "deleted_placement_sessions": int(deleted_placement_sessions or 0),
        "deleted_homework_submissions": int(deleted_homework_submissions or 0),
        "deleted_homeworks": int(deleted_homeworks or 0),
        "deleted_srs_state": int(deleted_srs_state or 0),
        "deleted_vocab_items": int(deleted_vocab_items or 0),
        "deleted_mistakes": int(deleted_mistakes or 0),
        "deleted_skill_snapshots": int(deleted_skill_snapshots or 0),
        "deleted_session_step_progress": int(deleted_session_step_progress or 0),
        "deleted_ai_usage_events": int(deleted_ai_usage_events or 0),
        "deleted_grammar_analysis_records": int(deleted_grammar_analysis_records or 0),
        "deleted_app_secrets": int(deleted_app_secrets or 0),
        "deleted_profiles": int(deleted_profiles or 0),
        "deleted_workspaces": int(deleted_workspaces or 0),
        "deleted_users": int(deleted_users or 0),
        "openai_key_cleared": openai_key_cleared,
    }
