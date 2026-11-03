"""Authenticated deterministic astrology conversation API."""
import asyncio
import hashlib
from datetime import datetime, timezone
import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.base import get_db
from app.models.entities import AIUsageLog, BirthChart, BirthProfile, ChatMessage, ChatSession, User
from app.schemas.api import (
    AIChatResponse,
    AIConversationCreate,
    AIConversationHistory,
    AIConversationList,
    AIConversationResponse,
    AIMessageCreate,
    AIMessageResponse,
    AIUsageResponse,
)
from app.services.ai.contracts import IntelligenceResponse
from app.services.ai.engine import engine_version, get_intelligence_engine
from app.services.ai.usage import daily_request_count, reserve_daily_request
from app.api.routes import current_user


router = APIRouter(prefix="/ai", tags=["AI Astrologer"])


def _owned_conversation(db: Session, conversation_id: UUID, user: User) -> ChatSession:
    conversation = db.scalar(select(ChatSession).where(
        ChatSession.id == conversation_id,
        ChatSession.user_id == user.id,
    ))
    if conversation is None:
        raise HTTPException(404, "Conversation not found")
    return conversation


def _conversation_response(db: Session, chat: ChatSession) -> AIConversationResponse:
    profile_name = None
    if chat.profile_id:
        profile_name = db.scalar(select(BirthProfile.display_name).where(BirthProfile.id == chat.profile_id))
    return AIConversationResponse(
        id=chat.id, profile_id=chat.profile_id, profile_name=profile_name, chart_id=chat.chart_id,
        astrology_system=chat.astrology_system, language=chat.language, title=chat.title,
        created_at=chat.created_at, updated_at=chat.updated_at,
    )


def _message_response(message: ChatMessage) -> AIMessageResponse:
    return AIMessageResponse(
        id=message.id, role=message.role, content=message.content, provider=message.provider,
        model=message.model, prompt_version=message.prompt_version,
        structured_response=message.response_data,
        input_tokens=message.input_tokens, output_tokens=message.output_tokens,
        created_at=message.created_at,
    )


def _usage_snapshot(db: Session, user_id: UUID, day_key: str) -> AIUsageResponse:
    used = daily_request_count(db, user_id, day_key)
    limit = max(0, settings.ai_free_daily_limit)
    return AIUsageResponse(daily_limit=limit, requests_used=used, remaining=max(0, limit - used))


def _reserve_request(db: Session, user: User, chat: ChatSession, content: str, request_key: str):
    now = datetime.now(timezone.utc)
    day_key = now.date().isoformat()
    usage_row = db.scalar(select(AIUsageLog).where(
        AIUsageLog.user_id == user.id,
        AIUsageLog.request_key == request_key,
        AIUsageLog.feature == "ai_chat",
    ))

    if usage_row is not None and usage_row.status == "completed":
        if usage_row.request_hash and usage_row.request_hash != hashlib.sha256(content.encode()).hexdigest():
            raise HTTPException(409, "Idempotency key was already used for different message content")
        message = db.get(ChatMessage, usage_row.message_id) if usage_row.message_id else None
        if message is None or message.role != "assistant" or message.session_id != chat.id:
            raise HTTPException(409, "This request completed without a replayable response")
        return usage_row, day_key, message
    if usage_row is not None and usage_row.status == "pending":
        if usage_row.request_hash and usage_row.request_hash != hashlib.sha256(content.encode()).hexdigest():
            raise HTTPException(409, "Idempotency key was already used for different message content")
        raise HTTPException(409, "This request is already in progress")
    if usage_row is not None and usage_row.status == "failed":
        if usage_row.request_hash and usage_row.request_hash != hashlib.sha256(content.encode()).hexdigest():
            raise HTTPException(409, "Idempotency key was already used for different message content")
        user_message = db.get(ChatMessage, usage_row.message_id) if usage_row.message_id else None
        if user_message is None or user_message.role != "user" or user_message.session_id != chat.id:
            raise HTTPException(409, "The failed request cannot be retried safely")
        changed = db.execute(update(AIUsageLog).where(
            AIUsageLog.id == usage_row.id, AIUsageLog.status == "failed"
        ).values(status="pending")).rowcount
        if not changed:
            db.rollback()
            raise HTTPException(409, "This request is already being retried")
        db.commit()
        return usage_row, usage_row.period_key, None

    limit = max(0, settings.ai_free_daily_limit)
    if not reserve_daily_request(db, user.id, day_key, limit, now):
        db.rollback()
        raise HTTPException(429, "Daily AI message limit reached. Try again tomorrow.")
    user_message = ChatMessage(session_id=chat.id, role="user", content=content, created_at=now)
    db.add(user_message)
    db.flush()
    if chat.title == "New conversation":
        chat.title = content[:157] + ("…" if len(content) > 160 else "")
    chat.updated_at = now
    usage_row = AIUsageLog(
        user_id=user.id,
        message_id=user_message.id,
        feature="ai_chat",
        period_key=day_key,
        request_key=request_key,
        request_hash=hashlib.sha256(content.encode()).hexdigest(),
        status="pending",
        input_tokens=0,
        output_tokens=0,
        cost=0,
        created_at=now,
    )
    db.add(usage_row)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        duplicate = db.scalar(select(AIUsageLog).where(
            AIUsageLog.user_id == user.id,
            AIUsageLog.request_key == request_key,
            AIUsageLog.feature == "ai_chat",
        ))
        if duplicate and duplicate.status == "completed" and duplicate.message_id:
            duplicate_message = db.get(ChatMessage, duplicate.message_id) if duplicate.message_id else None
            if duplicate_message is not None and duplicate_message.session_id == chat.id:
                return duplicate, duplicate.period_key, duplicate_message
        raise HTTPException(409, "A duplicate request is already being processed") from exc
    return usage_row, day_key, None


def _mark_failed(db: Session, usage_row: AIUsageLog) -> None:
    db.execute(update(AIUsageLog).where(
        AIUsageLog.id == usage_row.id, AIUsageLog.status == "pending"
    ).values(status="failed"))
    db.commit()


def _render_response(response: IntelligenceResponse) -> str:
    parts = [response.answer]
    parts.extend(section.text for section in response.sections if section.text != response.answer)
    return "\n\n".join(parts)


def _save_assistant_reply(db: Session, chat: ChatSession, usage_row: AIUsageLog, response: IntelligenceResponse) -> ChatMessage:
    now = datetime.now(timezone.utc)
    assistant = ChatMessage(
        session_id=chat.id,
        role="assistant",
        content=_render_response(response),
        response_data=response.model_dump(mode="json"),
        provider="deterministic",
        model=engine_version(),
        prompt_version=response.metadata.knowledge_base_version,
        input_tokens=0,
        output_tokens=0,
        created_at=now,
    )
    db.add(assistant)
    db.flush()
    db.execute(update(AIUsageLog).where(AIUsageLog.id == usage_row.id).values(
        message_id=assistant.id,
        input_tokens=0,
        output_tokens=0,
        status="completed",
    ))
    chat.updated_at = now
    db.commit()
    db.refresh(assistant)
    return assistant


@router.post("/conversations", response_model=AIConversationResponse, status_code=201)
def create_conversation(payload: AIConversationCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(BirthProfile).where(
        BirthProfile.id == payload.profile_id,
        BirthProfile.owner_id == user.id,
    ))
    if profile is None:
        raise HTTPException(404, "Profile not found")
    if payload.chart_id is not None:
        chart = db.scalar(select(BirthChart).join(BirthProfile, BirthProfile.id == BirthChart.profile_id).where(
            BirthChart.id == payload.chart_id,
            BirthChart.profile_id == profile.id,
            BirthChart.system == payload.astrology_system,
            BirthProfile.owner_id == user.id,
        ))
        if chart is None:
            raise HTTPException(404, "Chart not found")
    chat = ChatSession(
        user_id=user.id,
        profile_id=profile.id,
        chart_id=payload.chart_id,
        astrology_system=payload.astrology_system,
        language=payload.language,
        title=payload.title.strip(),
    )
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return _conversation_response(db, chat)


@router.get("/conversations", response_model=AIConversationList)
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    base_query = select(ChatSession).where(ChatSession.user_id == user.id)
    total = db.scalar(select(func.count()).select_from(base_query.subquery())) or 0
    chats = db.scalars(base_query.order_by(ChatSession.updated_at.desc()).offset(offset).limit(limit)).all()
    return AIConversationList(items=[_conversation_response(db, chat) for chat in chats], total=total)


@router.get("/conversations/{conversation_id}", response_model=AIConversationHistory)
def get_conversation(conversation_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    chat = _owned_conversation(db, conversation_id, user)
    messages = db.scalars(select(ChatMessage).where(ChatMessage.session_id == chat.id).order_by(ChatMessage.created_at, ChatMessage.id)).all()
    return AIConversationHistory(**_conversation_response(db, chat).model_dump(), messages=[_message_response(item) for item in messages])


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    chat = _owned_conversation(db, conversation_id, user)
    db.delete(chat)
    db.commit()


def _prepare_request(conversation_id: UUID, payload: AIMessageCreate, user: User, db: Session, request_key: str):
    chat = _owned_conversation(db, conversation_id, user)
    usage_row, day_key, replay_message = _reserve_request(db, user, chat, payload.content, request_key)
    return chat, usage_row, day_key, replay_message


def _build_response(db: Session, chat: ChatSession, user: User, content: str) -> IntelligenceResponse:
    return get_intelligence_engine().answer_for_session(db, chat, user, content)


def _stream_response_events(response: IntelligenceResponse):
    metadata = {"status": response.status.value, **response.metadata.model_dump(mode="json")}
    yield f"event: metadata\ndata: {json.dumps(metadata, ensure_ascii=False)}\n\n"
    summary = response.answer
    summary_data = {"content": summary + "\n\n"}
    yield f"event: delta\ndata: {json.dumps(summary_data, ensure_ascii=False)}\n\n"
    for section in response.sections:
        if section.text == summary:
            continue
        event_data = {
            "content": section.text + "\n\n",
            "section_type": section.section_type.value,
            "fact_ids": section.fact_ids,
            "rule_ids": section.rule_ids,
        }
        yield f"event: delta\ndata: {json.dumps(event_data, ensure_ascii=False)}\n\n"


@router.post("/conversations/{conversation_id}/messages", response_model=AIChatResponse)
async def send_message(
    conversation_id: UUID,
    payload: AIMessageCreate,
    request_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=80),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    request_key = request_key or str(uuid4())
    chat, usage_row, day_key, replay_message = _prepare_request(conversation_id, payload, user, db, request_key)
    if replay_message is not None:
        today = datetime.now(timezone.utc).date().isoformat()
        return AIChatResponse(message=_message_response(replay_message), usage=_usage_snapshot(db, user.id, today))
    try:
        response = _build_response(db, chat, user, payload.content)
    except Exception as exc:
        _mark_failed(db, usage_row)
        raise HTTPException(503, "The deterministic astrology response engine is unavailable") from exc
    assistant = _save_assistant_reply(db, chat, usage_row, response)
    return AIChatResponse(message=_message_response(assistant), usage=_usage_snapshot(db, user.id, day_key))


@router.post("/conversations/{conversation_id}/messages/stream")
async def stream_message(
    conversation_id: UUID,
    payload: AIMessageCreate,
    request_key: str | None = Header(default=None, alias="Idempotency-Key", max_length=80),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    request_key = request_key or str(uuid4())
    chat, usage_row, day_key, replay_message = _prepare_request(conversation_id, payload, user, db, request_key)

    if replay_message is not None:
        async def replay_events():
            if replay_message.response_data:
                response = IntelligenceResponse.model_validate(replay_message.response_data)
                for event in _stream_response_events(response):
                    yield event
            else:
                yield f"event: delta\ndata: {json.dumps({'content': replay_message.content}, ensure_ascii=False)}\n\n"
            today = datetime.now(timezone.utc).date().isoformat()
            data = AIChatResponse(message=_message_response(replay_message), usage=_usage_snapshot(db, user.id, today)).model_dump(mode="json")
            yield f"event: done\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        return StreamingResponse(replay_events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    try:
        response = _build_response(db, chat, user, payload.content)
    except Exception as exc:
        _mark_failed(db, usage_row)
        raise HTTPException(503, "The deterministic astrology response engine is unavailable") from exc

    async def events():
        try:
            for event in _stream_response_events(response):
                yield event
            assistant = _save_assistant_reply(db, chat, usage_row, response)
            data = AIChatResponse(message=_message_response(assistant), usage=_usage_snapshot(db, user.id, day_key)).model_dump(mode="json")
            yield f"event: done\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
        except (asyncio.CancelledError, GeneratorExit):
            _mark_failed(db, usage_row)
            raise
        except Exception:
            _mark_failed(db, usage_row)
            yield f"event: error\ndata: {json.dumps({'detail': 'The response could not be completed. Please try again.'})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
