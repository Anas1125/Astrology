"""Simple admin-only bilingual horoscope catalogue management.

A draft remains private until an administrator explicitly publishes its
English/Tamil pair. This is a lightweight content workflow, not a source or
peer-review certification system.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.routes import current_user
from app.db.base import get_db
from app.models.entities import HoroscopeContent, User

router = APIRouter(tags=["horoscope-admin"])


def _scope_key(system: str, period: str, sign: str, category: str, starts_on: date) -> str:
    raw = json.dumps(
        [system, period, sign, category, starts_on.isoformat()],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _require_admin(user: User) -> None:
    if (user.role or "").strip().upper() != "ADMIN":
        raise HTTPException(status_code=403, detail="Administrator access is required")


class HoroscopeDraftCreate(BaseModel):
    system: Literal["vedic", "western"]
    period: Literal["daily", "weekly", "monthly"]
    sign: str = Field(min_length=1, max_length=32)
    category: Literal["overview", "career", "relationships", "finance", "personal_growth"]
    starts_on: date
    ends_on: date
    en_content: str = Field(min_length=10, max_length=12000)
    ta_content: str = Field(min_length=10, max_length=12000)

    @field_validator("sign")
    @classmethod
    def clean_sign(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Sign is required")
        return value

    @field_validator("en_content", "ta_content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Both English and Tamil drafts must contain at least 10 characters")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError("End date must be on or after start date")
        return self


class HoroscopeDraftUpdate(BaseModel):
    starts_on: date
    ends_on: date
    en_content: str = Field(min_length=10, max_length=12000)
    ta_content: str = Field(min_length=10, max_length=12000)

    @field_validator("en_content", "ta_content")
    @classmethod
    def clean_content(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 10:
            raise ValueError("Both English and Tamil drafts must contain at least 10 characters")
        return value

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError("End date must be on or after start date")
        return self


def _records_for_scope(db: Session, scope_key: str) -> list[HoroscopeContent]:
    rows = list(db.scalars(select(HoroscopeContent)))
    return [
        row for row in rows
        if row.system and row.category
        and _scope_key(row.system, row.period, row.sign, row.category, row.starts_on) == scope_key
    ]


def _serialize_group(rows: list[HoroscopeContent]) -> dict:
    by_language = {row.language: row for row in rows}
    en, ta = by_language.get("en"), by_language.get("ta")
    primary = en or ta or rows[0]
    return {
        "scope_key": _scope_key(primary.system, primary.period, primary.sign, primary.category, primary.starts_on),
        "system": primary.system,
        "period": primary.period,
        "sign": primary.sign,
        "category": primary.category,
        "starts_on": primary.starts_on,
        "ends_on": primary.ends_on,
        "en_content": en.content if en else "",
        "ta_content": ta.content if ta else "",
        "languages_present": sorted(by_language),
        "published": bool(
            en and ta and en.approved and ta.approved
            and en.content.strip() and ta.content.strip()
            and en.starts_on == ta.starts_on and en.ends_on == ta.ends_on
        ),
    }


def _get_complete_pair(db: Session, scope_key: str) -> tuple[HoroscopeContent, HoroscopeContent]:
    rows = _records_for_scope(db, scope_key)
    by_language = {row.language: row for row in rows}
    if set(by_language) != {"en", "ta"}:
        raise HTTPException(status_code=404, detail="A complete English and Tamil horoscope pair was not found")
    en, ta = by_language["en"], by_language["ta"]
    if en.starts_on != ta.starts_on or en.ends_on != ta.ends_on:
        raise HTTPException(status_code=409, detail="English and Tamil entries must use the same date range")
    if not en.content.strip() or not ta.content.strip():
        raise HTTPException(status_code=422, detail="Both English and Tamil versions are required")
    return en, ta




class HoroscopeBulkImport(BaseModel):
    """A single upload containing up to 5,000 bilingual horoscope draft rows."""
    items: list[HoroscopeDraftCreate] = Field(min_length=1, max_length=5000)


@router.post("/admin/horoscope/content/bulk-import")
def bulk_import_horoscope_content(
    payload: HoroscopeBulkImport,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Create bilingual drafts from one validated CSV upload. Nothing is published."""
    _require_admin(user)

    dates = {item.starts_on for item in payload.items}
    systems = {item.system for item in payload.items}
    periods = {item.period for item in payload.items}
    signs = {item.sign for item in payload.items}
    categories = {item.category for item in payload.items}

    existing_rows = list(db.scalars(select(HoroscopeContent).where(
        HoroscopeContent.starts_on.in_(dates),
        HoroscopeContent.system.in_(systems),
        HoroscopeContent.period.in_(periods),
        HoroscopeContent.sign.in_(signs),
        HoroscopeContent.category.in_(categories),
        HoroscopeContent.language.in_(("en", "ta")),
    )))
    existing_keys = {
        (row.system, row.period, row.sign, row.category, row.starts_on, row.language)
        for row in existing_rows
    }

    seen_scopes = set()
    new_rows = []
    skipped = 0
    for item in payload.items:
        scope = (item.system, item.period, item.sign, item.category, item.starts_on)
        en_key = (*scope, "en")
        ta_key = (*scope, "ta")

        # Skip duplicates already in the database and repeated rows in this file.
        if scope in seen_scopes or en_key in existing_keys or ta_key in existing_keys:
            skipped += 1
            continue

        seen_scopes.add(scope)
        existing_keys.add(en_key)
        existing_keys.add(ta_key)
        common = {
            "system": item.system,
            "period": item.period,
            "sign": item.sign,
            "category": item.category,
            "starts_on": item.starts_on,
            "ends_on": item.ends_on,
            "approved": False,
            "source_references": [],
            "source_verified": False,
            "editorial_reviewed": False,
        }
        new_rows.append(HoroscopeContent(**common, language="en", content=item.en_content))
        new_rows.append(HoroscopeContent(**common, language="ta", content=item.ta_content))

    try:
        db.add_all(new_rows)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="The import conflicted with an existing horoscope entry. No rows from this upload were saved; refresh and try again.",
        ) from exc

    return {
        "created": len(new_rows) // 2,
        "skipped": skipped,
        "status": "drafts_created",
    }




@router.post("/admin/horoscope/content/publish-all")
def publish_all_horoscope_content(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    """Publish every complete bilingual horoscope draft in one transaction."""
    _require_admin(user)

    rows = list(db.scalars(select(HoroscopeContent).where(
        HoroscopeContent.system.is_not(None),
        HoroscopeContent.category.is_not(None),
    )))
    groups: dict[str, list[HoroscopeContent]] = {}
    for row in rows:
        key = _scope_key(row.system, row.period, row.sign, row.category, row.starts_on)
        groups.setdefault(key, []).append(row)

    published = 0
    skipped = 0
    for group in groups.values():
        by_language = {row.language: row for row in group}
        english = by_language.get("en")
        tamil = by_language.get("ta")

        # Keep the existing safety rule: only matching, complete EN/TA pairs publish.
        if (
            english is None or tamil is None
            or english.starts_on != tamil.starts_on
            or english.ends_on != tamil.ends_on
            or not english.content.strip()
            or not tamil.content.strip()
        ):
            skipped += 1
            continue

        if english.approved and tamil.approved:
            continue

        english.approved = True
        tamil.approved = True
        published += 1

    db.commit()
    return {
        "published": published,
        "skipped": skipped,
        "status": "published",
    }


@router.get("/admin/horoscope/content")
def list_horoscope_content(user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    rows = list(db.scalars(select(HoroscopeContent).order_by(HoroscopeContent.starts_on.desc(), HoroscopeContent.sign.asc())))
    groups: dict[str, list[HoroscopeContent]] = {}
    for row in rows:
        if not row.system or not row.category:
            continue
        key = _scope_key(row.system, row.period, row.sign, row.category, row.starts_on)
        groups.setdefault(key, []).append(row)
    items = [_serialize_group(group) for group in groups.values()]
    items.sort(key=lambda item: (item["starts_on"], item["sign"]), reverse=True)
    return {"items": items}


@router.post("/admin/horoscope/content", status_code=status.HTTP_201_CREATED)
def create_horoscope_draft(payload: HoroscopeDraftCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    duplicate = db.scalar(select(HoroscopeContent.id).where(
        HoroscopeContent.system == payload.system,
        HoroscopeContent.period == payload.period,
        HoroscopeContent.sign == payload.sign,
        HoroscopeContent.category == payload.category,
        HoroscopeContent.starts_on == payload.starts_on,
    ))
    if duplicate:
        raise HTTPException(status_code=409, detail="A horoscope entry already exists for this selection and start date")
    try:
        for language, content in (("en", payload.en_content), ("ta", payload.ta_content)):
            db.add(HoroscopeContent(
                system=payload.system,
                period=payload.period,
                sign=payload.sign,
                category=payload.category,
                language=language,
                starts_on=payload.starts_on,
                ends_on=payload.ends_on,
                content=content,
                approved=False,
                source_references=[],
                source_verified=False,
                editorial_reviewed=False,
                reviewed_by=None,
                reviewed_at=None,
            ))
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="A matching horoscope entry already exists") from exc
    return {
        "scope_key": _scope_key(payload.system, payload.period, payload.sign, payload.category, payload.starts_on),
        "status": "draft",
    }


@router.put("/admin/horoscope/content/{scope_key}")
def update_horoscope_content(scope_key: str, payload: HoroscopeDraftUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    en, ta = _get_complete_pair(db, scope_key)
    old_key = scope_key
    try:
        for row, content in ((en, payload.en_content), (ta, payload.ta_content)):
            row.starts_on = payload.starts_on
            row.ends_on = payload.ends_on
            row.content = content
            # Any edit returns the pair to draft so the administrator must
            # explicitly publish the updated version again.
            row.approved = False
            row.source_references = []
            row.source_verified = False
            row.editorial_reviewed = False
            row.reviewed_by = None
            row.reviewed_at = None
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Another horoscope entry already uses this selection and start date") from exc
    return {
        "scope_key": _scope_key(en.system, en.period, en.sign, en.category, payload.starts_on),
        "previous_scope_key": old_key,
        "status": "draft_updated",
    }


@router.post("/admin/horoscope/content/{scope_key}/publish")
def publish_horoscope_content(scope_key: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    en, ta = _get_complete_pair(db, scope_key)
    en.approved = True
    ta.approved = True
    db.commit()
    return _serialize_group([en, ta])


@router.post("/admin/horoscope/content/{scope_key}/unpublish")
def unpublish_horoscope_content(scope_key: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    en, ta = _get_complete_pair(db, scope_key)
    en.approved = False
    ta.approved = False
    db.commit()
    return _serialize_group([en, ta])


@router.delete("/admin/horoscope/content/{scope_key}")
def delete_horoscope_content(scope_key: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    _require_admin(user)
    en, ta = _get_complete_pair(db, scope_key)
    db.delete(en)
    db.delete(ta)
    db.commit()
    return {"scope_key": scope_key, "status": "deleted"}
