from uuid import UUID
from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
import secrets
import jwt
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.models.entities import BirthChart, BirthProfile, ChartCalculationRun, CompatibilityReport, PasswordResetToken, SecurityAuditEvent, User
from app.schemas.api import AccountResponse, AstrologyChartRequest, VedicChartRequest, CalculationResultResponse, VedicDignityResponse, ChartCreate, ChartResponse, ChartHistoryItem, ChartHistoryPage, PanchangRequest, HoroscopeRequest, HoroscopeAvailabilityResponse, LocationSuggestion, CompatibilityRequest, ProfileCreate, ProfilePatch, ProfileResponse, RegisterRequest, TokenResponse, ForgotPasswordRequest, PasswordResetRequest, PasswordResetRequestResponse, PasswordResetResponse
from app.services.astrology import EngineUnavailable, VedicAstrologyEngine, WesternAstrologyEngine
from app.services.astrology.vedic import VEDIC_ENGINE_VERSION
from app.services.astrology.western import DEFAULT_ASPECT_ORBS, WESTERN_ENGINE_VERSION
from app.services.astrology.sweph import ENGINE_VERSION, InvalidBirthData
from app.services.astrology.panchang import PanchangUnavailable, calculate_panchang_day
from app.services.astrology.vedic_dignity import DignityInputError, analyze_vedic_d1_dignity
from app.services.astrology.compatibility.ashtakoota import calculate_ashtakoota
from app.services.astrology.compatibility.ashtakoota_api import CompatibilityChartError, extract_d1_lahiri_moon_longitude
from app.services.password_reset_email import deliver_reset_link
from app.services.security_limits import client_ip_for_rate_limit, consume_rate_limit
from app.services.geocoding import GeocodingUnavailable, search_places

router = APIRouter()
logger = logging.getLogger(__name__)
oauth = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
def _calculation_unavailable(reason_code: str, system: str) -> HTTPException:
    messages = {
        "feature_disabled": "Astrology calculations are currently disabled intentionally while verified runtime setup and Swiss Ephemeris licensing approval are pending. No calculation was performed and no chart was saved.",
        "license_unconfirmed": "Astrology calculations are blocked pending Swiss Ephemeris licensing approval. No calculation was performed and no chart was saved.",
        "ephemeris_data_unavailable": "Swiss Ephemeris data is unavailable for this calculation. No calculation was performed and no chart was saved.",
        "native_runtime_unavailable": "The Swiss Ephemeris native runtime is unavailable. No calculation was performed and no chart was saved.",
    }
    logger.warning("astrology calculation unavailable", extra={"reason_code": reason_code, "calculation_system": system})
    return HTTPException(503, messages.get(reason_code, messages["native_runtime_unavailable"]))


def current_user(token: str = Depends(oauth), db: Session = Depends(get_db)) -> User:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        uid = claims["sub"]
        auth_version = claims.get("ver", 0)
        user = db.get(User, UUID(uid))
    except (jwt.PyJWTError, ValueError, KeyError):
        user = None
        auth_version = None
    if user is None or not user.is_active or auth_version != user.auth_version:
        raise HTTPException(status_code=401, detail="Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"})
    return user


@router.post("/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(409, "An account with this email already exists")
    user = User(email=payload.email, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(str(user.id), user.auth_version))


@router.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), remember_me: bool = Form(False), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form_data.username))
    if not user or not user.is_active or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    token_minutes = 30 * 24 * 60 if remember_me else 8 * 60
    return TokenResponse(access_token=create_access_token(str(user.id), user.auth_version, expires_minutes=token_minutes))


def _reset_service_configured() -> bool:
    return settings.password_reset_email_configured or settings.password_reset_local_file_configured


def _deliver_password_reset_safely(email: str, reset_url: str, reset_id: UUID, db: Session) -> None:
    try:
        deliver_reset_link(email, reset_url)
    except Exception as exc:
        now = datetime.now(timezone.utc)
        db.execute(update(PasswordResetToken).where(PasswordResetToken.id == reset_id).values(
            consumed_at=now,
        ).execution_options(synchronize_session=False))
        reset = db.get(PasswordResetToken, reset_id)
        if reset is not None:
            db.add(SecurityAuditEvent(user_id=reset.user_id, event_type="password_reset_delivery_failed", created_at=now))
        db.commit()
        logger.warning("password reset delivery failed", extra={"error_type": type(exc).__name__})


@router.post("/auth/forgot-password", response_model=PasswordResetRequestResponse, status_code=202)
def forgot_password(
    payload: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    if not _reset_service_configured():
        raise HTTPException(503, "Password reset email delivery is not configured. Contact the administrator.")

    now = datetime.now(timezone.utc)
    client_ip = client_ip_for_rate_limit(request)
    if not consume_rate_limit(
        db, f"password-reset:ip:{client_ip}", limit=settings.password_reset_ip_rate_limit_per_hour,
        window_seconds=3600, now=now,
    ):
        raise HTTPException(429, "Too many password reset requests. Try again later.")
    normalized_email = str(payload.email).strip().casefold()
    if not consume_rate_limit(
        db, f"password-reset:email:{normalized_email}", limit=settings.password_reset_rate_limit_per_hour,
        window_seconds=3600, now=now,
    ):
        raise HTTPException(429, "Too many password reset requests. Try again later.")

    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email, User.is_active.is_(True)))
    if user is not None:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        db.execute(update(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.consumed_at.is_(None)
        ).values(consumed_at=now))
        reset = PasswordResetToken(
            user_id=user.id, token_hash=token_hash,
            expires_at=now + timedelta(minutes=30), created_at=now,
        )
        db.add(reset)
        db.add(SecurityAuditEvent(user_id=user.id, event_type="password_reset_requested", created_at=now))
        db.commit()
        reset_url = f"{settings.password_reset_frontend_url.rstrip('/')}/reset-password#token={raw_token}"
        background_tasks.add_task(_deliver_password_reset_safely, user.email, reset_url, reset.id, db)
    return PasswordResetRequestResponse(
        message="If the address is registered and delivery is available, password reset instructions will be sent."
    )


@router.post("/auth/reset-password", response_model=PasswordResetResponse)
def reset_password(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    client_ip = client_ip_for_rate_limit(request)
    if not consume_rate_limit(
        db, f"password-reset-complete:ip:{client_ip}", limit=10, window_seconds=900, now=now,
    ):
        raise HTTPException(429, "Too many password reset attempts. Try again later.")

    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    reset = db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
    expires_at = reset.expires_at if reset else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if reset is None or reset.consumed_at is not None or expires_at <= now:
        raise HTTPException(400, "This password reset link is invalid or expired.")
    changed = db.execute(update(PasswordResetToken).where(
        PasswordResetToken.id == reset.id,
        PasswordResetToken.consumed_at.is_(None),
        PasswordResetToken.expires_at > now,
    ).values(consumed_at=now).execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        db.rollback()
        raise HTTPException(400, "This password reset link is invalid or expired.")
    user = db.get(User, reset.user_id)
    if user is None or not user.is_active:
        db.rollback()
        raise HTTPException(400, "This password reset link is invalid or expired.")
    user.password_hash = hash_password(payload.new_password)
    user.auth_version += 1
    db.execute(update(PasswordResetToken).where(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.id != reset.id,
        PasswordResetToken.consumed_at.is_(None),
    ).values(consumed_at=now).execution_options(synchronize_session=False))
    db.add(SecurityAuditEvent(user_id=user.id, event_type="password_reset_completed", created_at=now))
    db.commit()
    return PasswordResetResponse(message="Password updated. Please sign in with your new password.")


@router.get("/auth/me", response_model=AccountResponse)
def get_current_account(user: User = Depends(current_user)):
    return AccountResponse(id=user.id, email=user.email, role=user.role)


@router.get("/profiles", response_model=list[ProfileResponse])
def list_profiles(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(BirthProfile).where(BirthProfile.owner_id == user.id).order_by(BirthProfile.created_at.desc())))


@router.get("/profiles/location-search", response_model=list[LocationSuggestion])
def search_birthplaces(q: str = Query(min_length=3, max_length=120), language: str = Query(default="en", pattern="^(en|ta)$"),
                       user: User = Depends(current_user), db: Session = Depends(get_db)):
    query = q.strip()
    if len(query) < 3:
        raise HTTPException(422, "Enter at least three characters to search for a place")
    if not settings.geoapify_api_key:
        raise HTTPException(503, "Birthplace search is not configured on this server. You can enter location details manually.")
    if not consume_rate_limit(db, f"geocoding:user:{user.id}", limit=settings.geocoding_rate_limit_per_minute, window_seconds=60):
        raise HTTPException(429, "Too many birthplace searches. Please wait a moment and try again.")
    try:
        return search_places(query, api_key=settings.geoapify_api_key, language=language,
                             timeout=settings.geocoding_request_timeout_seconds)
    except GeocodingUnavailable as exc:
        raise HTTPException(502, "Birthplace search is temporarily unavailable. You can enter location details manually.") from exc


@router.post("/profiles", response_model=ProfileResponse, status_code=201)
def create_profile(payload: ProfileCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = BirthProfile(owner_id=user.id, **payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
def get_profile(profile_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(BirthProfile).where(BirthProfile.id == profile_id, BirthProfile.owner_id == user.id))
    if profile is None:
        raise HTTPException(404, "Profile not found")
    return profile


@router.patch("/profiles/{profile_id}", response_model=ProfileResponse)
def update_profile(profile_id: UUID, payload: ProfilePatch, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(BirthProfile).where(BirthProfile.id == profile_id, BirthProfile.owner_id == user.id))
    if profile is None:
        raise HTTPException(404, "Profile not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/profiles/{profile_id}", status_code=204)
def delete_profile(profile_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(BirthProfile).where(BirthProfile.id == profile_id, BirthProfile.owner_id == user.id))
    if profile is None:
        raise HTTPException(404, "Profile not found")
    db.delete(profile)
    db.commit()


@router.post("/astrology/charts", response_model=ChartResponse, status_code=202)
def create_chart(payload: ChartCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profile = db.scalar(select(BirthProfile).where(BirthProfile.id == payload.profile_id, BirthProfile.owner_id == user.id))
    if profile is None:
        raise HTTPException(404, "Profile not found")
    chart = BirthChart(profile_id=profile.id, system=payload.system, division=payload.division,
                       status="unavailable", unavailable_reason="No commercially cleared, verified ephemeris engine is configured. No planetary positions were fabricated.")
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return chart


def _chart_input_snapshot(profile: BirthProfile) -> dict:
    return {
        "profile_id": str(profile.id),
        "display_name": profile.display_name,
        "birth_date": profile.birth_date.isoformat(),
        "birth_time": profile.birth_time.isoformat() if profile.birth_time else None,
        "time_accuracy": profile.time_accuracy,
        "birthplace": profile.birthplace,
        "country": profile.country,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
        "timezone": profile.timezone,
    }


def _calculation_response(chart: BirthChart, run: ChartCalculationRun) -> CalculationResultResponse:
    return CalculationResultResponse(
        chart_id=chart.id,
        calculation_run_id=run.id,
        profile_id=chart.profile_id,
        calculation_system=chart.system,
        status=run.status,
        engine_version=run.engine_version,
        ephemeris_version=run.ephemeris_version,
        configuration=run.config,
        input_snapshot=run.input_snapshot,
        result=run.result,
        calculated_at=run.created_at,
    )


def _calculate_owned_profile(payload: AstrologyChartRequest | VedicChartRequest, system: str, user: User, db: Session):
    profile = db.scalar(select(BirthProfile).where(BirthProfile.id == payload.profile_id, BirthProfile.owner_id == user.id))
    if profile is None:
        raise HTTPException(404, "Profile not found")
    limited_chart = profile.birth_time is None or profile.time_accuracy == "unknown"
    if profile.latitude is None or profile.longitude is None or not profile.timezone:
        raise HTTPException(422, "Select a birthplace from the location suggestions so coordinates and an IANA timezone are saved")
    if limited_chart and system == "vedic" and payload.division != "D1":
        raise HTTPException(422, "D9 Navamsa requires a known birth time; use D1 Rashi for a date-only chart")
    engine = VedicAstrologyEngine() if system == "vedic" else WesternAstrologyEngine()
    division = payload.division if system == "vedic" else "D1"
    try:
        provider = engine.get_provider()
    except EngineUnavailable as exc:
        raise _calculation_unavailable(exc.reason_code, system) from exc
    calculation_config = {"house_system": payload.house_system, "chart_mode": "limited_date_only" if limited_chart else "full_timed"}
    if system == "vedic":
        calculation_config.update({"zodiac": "sidereal", "ayanamsa": "lahiri", "division": payload.division,
                                   "dasha_year_convention": payload.dasha_year_convention})
    else:
        effective_orbs = dict(DEFAULT_ASPECT_ORBS)
        effective_orbs.update(payload.aspect_orbs or {})
        calculation_config.update({"zodiac": "tropical", "aspect_orbs": effective_orbs})
    snapshot = _chart_input_snapshot(profile)
    engine_version = f"{ENGINE_VERSION}+{VEDIC_ENGINE_VERSION}" if system == "vedic" else f"{ENGINE_VERSION}+{WESTERN_ENGINE_VERSION}"
    key_payload = {"input": snapshot, "system": system, "configuration": calculation_config, "engine": engine_version, "ephemeris": provider.ephemeris_version}
    calculation_key = hashlib.sha256(json.dumps(key_payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    existing_run = db.scalar(select(ChartCalculationRun).where(ChartCalculationRun.calculation_key == calculation_key))
    if existing_run:
        existing_chart = db.get(BirthChart, existing_run.chart_id)
        if existing_chart:
            return _calculation_response(existing_chart, existing_run)
    birth_data = {
        "birth_date": profile.birth_date,
        "birth_time": profile.birth_time,
        "time_accuracy": profile.time_accuracy,
        "timezone": profile.timezone,
        "latitude": profile.latitude,
        "longitude": profile.longitude,
    }
    try:
        result = engine.calculate_chart(birth_data, calculation_config)
    except InvalidBirthData as exc:
        raise HTTPException(422, str(exc)) from exc
    except EngineUnavailable as exc:
        raise _calculation_unavailable(exc.reason_code, system) from exc
    calculated_at = datetime.now(timezone.utc)
    result["calculated_at"] = calculated_at.isoformat()
    config_snapshot = {
        **calculation_config,
        "vedic_engine_version": VEDIC_ENGINE_VERSION if system == "vedic" else None,
        "western_engine_version": WESTERN_ENGINE_VERSION if system == "western" else None,
        "calculation_flags": result["calculation_flags"],
        "ephemeris_path_configured": True,
        "time_accuracy": profile.time_accuracy,
    }
    chart = BirthChart(
        profile_id=profile.id,
        system=system,
        division=division,
        status="complete",
        unavailable_reason="",
        config=config_snapshot,
        engine_version=engine_version,
        ephemeris_version=result["ephemeris_version"],
    )
    db.add(chart)
    db.flush()
    run = ChartCalculationRun(
        chart_id=chart.id,
        run_number=1,
        status="complete",
        config=config_snapshot,
        input_snapshot=snapshot,
        calculation_key=calculation_key,
        result=result,
        engine_version=engine_version,
        ephemeris_version=result["ephemeris_version"],
        timezone_assumption=(f"{profile.timezone}: local noon estimate used because birth time is unknown" if limited_chart else f"{profile.timezone}: local wall time converted using system IANA timezone data"),
        created_at=calculated_at,
    )
    db.add(run)
    db.commit()
    db.refresh(chart)
    db.refresh(run)
    return _calculation_response(chart, run)


@router.post("/astrology/charts/vedic", response_model=CalculationResultResponse, status_code=201)
def calculate_vedic_chart(payload: VedicChartRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _calculate_owned_profile(payload, "vedic", user, db)


@router.post("/astrology/charts/western", response_model=CalculationResultResponse, status_code=201)
def calculate_western_chart(payload: AstrologyChartRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _calculate_owned_profile(payload, "western", user, db)


@router.post("/panchang/daily")
def calculate_daily_panchang(payload: PanchangRequest, user: User = Depends(current_user)):
    # Reuse the same feature and license gates as natal chart calculation.
    del user
    try:
        provider = VedicAstrologyEngine().get_provider()
    except EngineUnavailable as exc:
        raise _calculation_unavailable(exc.reason_code, "panchang") from exc
    try:
        return calculate_panchang_day(
            payload.local_date,
            payload.latitude,
            payload.longitude,
            payload.timezone,
            provider,
            location_name=payload.location_name,
        )
    except InvalidBirthData as exc:
        raise HTTPException(422, str(exc)) from exc
    except PanchangUnavailable as exc:
        logger.warning("Panchang calculation unavailable", extra={"reason_code": "sun_event_or_ephemeris_unavailable"})
        raise HTTPException(503, "A verified sunrise, sunset, or Swiss Ephemeris result is unavailable for this local date and location.") from exc


@router.post("/horoscope/daily", response_model=HoroscopeAvailabilityResponse)
def daily_horoscope(payload: HoroscopeRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    chart_id = None
    if payload.mode == "personalized":
        profile = db.scalar(select(BirthProfile).where(
            BirthProfile.id == payload.profile_id,
            BirthProfile.owner_id == user.id,
        ))
        if profile is None:
            raise HTTPException(404, "Profile not found")
        if payload.chart_id is not None:
            selected_chart = db.scalar(select(BirthChart).where(
                BirthChart.id == payload.chart_id,
                BirthChart.profile_id == profile.id,
                BirthChart.system == payload.system,
            ))
            if selected_chart is None:
                raise HTTPException(404, "Chart not found")
            chart_row = db.execute(
                select(BirthChart.id, ChartCalculationRun.result)
                .join(ChartCalculationRun, ChartCalculationRun.chart_id == BirthChart.id)
                .where(BirthChart.id == selected_chart.id, BirthChart.status == "complete", ChartCalculationRun.status == "complete")
                .order_by(ChartCalculationRun.created_at.desc())
            ).first()
        else:
            chart_row = db.execute(
                select(BirthChart.id, ChartCalculationRun.result)
                .join(ChartCalculationRun, ChartCalculationRun.chart_id == BirthChart.id)
                .where(BirthChart.profile_id == profile.id, BirthChart.system == payload.system,
                       BirthChart.status == "complete", ChartCalculationRun.status == "complete")
                .order_by(ChartCalculationRun.created_at.desc())
            ).first()
        if chart_row and isinstance(chart_row.result, dict) and chart_row.result:
            chart_id = str(chart_row.id)
    reason = "no_matching_content"
    content = None
    source_references: list[dict | str] = []
    status_value = "unavailable"
    if payload.mode == "personalized" and chart_id is None:
        reason = "completed_chart_required"
        status_value = "missing_chart"
    elif payload.mode == "personalized":
        # Personal content requires explicit chart-fact based material. The
        # sign-based catalogue is never applied to a personal chart implicitly.
        reason = "personalized_content_not_available"
    else:
        from app.models.entities import HoroscopeContent
        candidates = list(db.scalars(select(HoroscopeContent).where(
            HoroscopeContent.system == payload.system,
            HoroscopeContent.period == payload.period,
            HoroscopeContent.sign == payload.sign,
            HoroscopeContent.category == payload.category,
            HoroscopeContent.starts_on <= payload.local_date,
            HoroscopeContent.ends_on >= payload.local_date,
        )))
        if not db.scalar(select(func.count()).select_from(HoroscopeContent)):
            reason = "catalogue_empty"
        elif not candidates:
            same_scope = db.scalar(select(func.count()).select_from(HoroscopeContent).where(
                HoroscopeContent.system == payload.system,
                HoroscopeContent.period == payload.period,
                HoroscopeContent.sign == payload.sign,
                HoroscopeContent.category == payload.category,
            ))
            reason = "content_not_available_for_date" if same_scope else "no_matching_content"
        else:
            by_language = {item.language: item for item in candidates}
            english_record, tamil_record = by_language.get("en"), by_language.get("ta")
            # In the simple catalogue, `approved` is the explicit Publish toggle.
            # We still require a complete, matching English/Tamil pair.
            def eligible(item):
                return bool(item and item.approved and item.content and item.content.strip())
            bilingual_pair = (english_record and tamil_record
                              and english_record.starts_on == tamil_record.starts_on
                              and english_record.ends_on == tamil_record.ends_on
                              and eligible(english_record) and eligible(tamil_record))
            if bilingual_pair:
                selected = by_language[payload.language]
                content = selected.content
                source_references = selected.source_references or []
                reason = "approved_content_available"
                status_value = "available"
            else:
                reason = "awaiting_bilingual_editorial_review"
    messages = {
        "catalogue_empty": (
            "The horoscope catalogue is empty. No content has been authored or reviewed for this feature. No prediction was generated.",
            "ராசிபலன் உள்ளடக்கப் பட்டியல் காலியாக உள்ளது. இந்த அம்சத்திற்கான உள்ளடக்கம் எழுதப்படவோ மதிப்பாய்வு செய்யப்படவோ இல்லை. எந்தக் கணிப்பும் உருவாக்கப்படவில்லை.",
        ),
        "no_matching_content": (
            "There is no content for this tradition, sign, period and topic combination. No prediction was generated.",
            "இந்த மரபு, ராசி, காலம் மற்றும் தலைப்புக்கான உள்ளடக்கம் இல்லை. எந்தக் கணிப்பும் உருவாக்கப்படவில்லை.",
        ),
        "content_not_available_for_date": (
            "Content exists for this selection, but not for the chosen date. No prediction was generated.",
            "இந்தத் தேர்வுக்கு உள்ளடக்கம் உள்ளது; ஆனால் தேர்ந்தெடுத்த தேதிக்கானது இல்லை. எந்தக் கணிப்பும் உருவாக்கப்படவில்லை.",
        ),
        "awaiting_bilingual_editorial_review": (
            "A matching English and Tamil horoscope pair has not been published yet. No content was shown.",
            "பொருந்தும் ஆங்கிலம் மற்றும் தமிழ் ராசிபலன் இன்னும் வெளியிடப்படவில்லை. உள்ளடக்கம் காட்டப்படவில்லை.",
        ),
        "completed_chart_required": (
            "A completed saved chart for this profile and system is required. No personal chart facts or predictions were generated.",
            "இந்த விவரத்திற்கும் முறைக்கும் முடிக்கப்பட்ட சேமித்த ஜாதகம் தேவை. தனிப்பட்ட ஜாதகத் தகவலோ கணிப்போ உருவாக்கப்படவில்லை.",
        ),
        "personalized_content_not_available": (
            "No reviewed chart-specific horoscope content is available for this saved chart. No personal prediction was generated.",
            "இந்தச் சேமித்த ஜாதகத்திற்கான மதிப்பாய்வு செய்யப்பட்ட தனிப்பட்ட உள்ளடக்கம் இல்லை. எந்தத் தனிப்பட்ட கணிப்பும் உருவாக்கப்படவில்லை.",
        ),
        "approved_content_available": (
            "Curated general zodiac content is available. It is tradition-specific, not a personalized prediction, and astrology is not scientifically established.",
            "தொகுக்கப்பட்ட பொதுவான ராசி உள்ளடக்கம் கிடைக்கிறது. இது மரபு சார்ந்தது; தனிப்பட்ட கணிப்பு அல்ல. ஜோதிடம் அறிவியல் ரீதியாக நிறுவப்படவில்லை.",
        ),
    }
    english, tamil = messages[reason]
    return {
        "status": status_value,
        "mode": payload.mode,
        "system": payload.system,
        "local_date": payload.local_date.isoformat(),
        "period": payload.period,
        "category": payload.category,
        "sign": payload.sign,
        "chart_id": chart_id,
        "content": content,
        "source_references": source_references,
        "reason": reason,
        "message": (tamil if payload.language == "ta" else english) if status_value != "available" else ("This is curated general zodiac content, not a personalized prediction. Astrology is a traditional belief system and is not scientifically established." if payload.language == "en" else "இது தொகுக்கப்பட்ட பொதுவான ராசி உள்ளடக்கம்; தனிப்பட்ட கணிப்பு அல்ல. ஜோதிடம் ஒரு பாரம்பரிய நம்பிக்கை முறை; இது அறிவியல் ரீதியாக நிறுவப்படவில்லை."),
    }


@router.post("/compatibility/check")
def compatibility_availability(payload: CompatibilityRequest, user: User = Depends(current_user), db: Session = Depends(get_db)):
    profiles = list(db.scalars(select(BirthProfile).where(
        BirthProfile.id.in_([payload.profile_a_id, payload.profile_b_id]),
        BirthProfile.owner_id == user.id,
    )))
    if len(profiles) != 2:
        raise HTTPException(404, "One or both profiles not found")

    selected_chart_ids: list[str | None] = [None, None]

    if payload.chart_a_id and payload.chart_b_id:
        selected = (
            (payload.profile_a_id, payload.chart_a_id),
            (payload.profile_b_id, payload.chart_b_id),
        )
        for index, (profile_id, chart_id) in enumerate(selected):
            owned_chart = db.scalar(
                select(BirthChart)
                .join(BirthProfile, BirthProfile.id == BirthChart.profile_id)
                .where(BirthChart.id == chart_id, BirthProfile.owner_id == user.id)
            )
            if (
                owned_chart is None
                or owned_chart.profile_id != profile_id
                or owned_chart.system != payload.system
            ):
                raise HTTPException(404, "Chart not found")

            completed = db.scalar(
                select(ChartCalculationRun.id)
                .where(
                    ChartCalculationRun.chart_id == chart_id,
                    ChartCalculationRun.status == "complete",
                    ChartCalculationRun.result.is_not(None),
                )
                .order_by(ChartCalculationRun.created_at.desc())
                .limit(1)
            )
            if owned_chart.status == "complete" and completed is not None:
                selected_chart_ids[index] = str(chart_id)
    else:
        chart_filters = [
            BirthChart.profile_id.in_([payload.profile_a_id, payload.profile_b_id]),
            BirthChart.system == payload.system,
            BirthChart.status == "complete",
            ChartCalculationRun.status == "complete",
            ChartCalculationRun.result.is_not(None),
        ]
        # Do not accidentally select a D9 chart for Ashtakoota.
        if payload.system == "vedic":
            chart_filters.append(BirthChart.division == "D1")

        completed_rows = db.execute(
            select(BirthChart.profile_id, BirthChart.id)
            .join(ChartCalculationRun, ChartCalculationRun.chart_id == BirthChart.id)
            .where(*chart_filters)
            .order_by(ChartCalculationRun.created_at.desc())
        ).all()

        latest_by_profile = {}
        for profile_id, chart_id in completed_rows:
            latest_by_profile.setdefault(profile_id, chart_id)

        selected_chart_ids = [
            str(latest_by_profile[profile_id])
            if profile_id in latest_by_profile else None
            for profile_id in (payload.profile_a_id, payload.profile_b_id)
        ]

    completed_chart_count = sum(chart_id is not None for chart_id in selected_chart_ids)
    if completed_chart_count < 2:
        return {
            "status": "missing_charts",
            "system": payload.system,
            "profiles_checked": 2,
            "completed_chart_count": int(completed_chart_count),
            "chart_ids": selected_chart_ids,
            "score": None,
            "factors": [],
            "reason": "completed_charts_required",
            "message": (
                "Two completed saved Vedic D1 charts are required for Ashtakoota."
                if payload.system == "vedic"
                else "Two completed saved charts for the selected system are required."
            ),
        }

    # Preserve the prior Western availability-only behaviour.
    if payload.system == "western":
        return {
            "status": "unavailable",
            "system": "western",
            "profiles_checked": 2,
            "completed_chart_count": int(completed_chart_count),
            "chart_ids": selected_chart_ids,
            "score": None,
            "factors": [],
            "reason": "reviewed_compatibility_method_unavailable",
            "message": "No Western compatibility score is produced by this endpoint.",
        }

    run_records = []
    moon_longitudes = []
    for profile_id, chart_id in zip(
        (payload.profile_a_id, payload.profile_b_id),
        selected_chart_ids,
        strict=True,
    ):
        chart = db.scalar(
            select(BirthChart)
            .join(BirthProfile, BirthProfile.id == BirthChart.profile_id)
            .where(
                BirthChart.id == UUID(chart_id),
                BirthChart.profile_id == profile_id,
                BirthProfile.owner_id == user.id,
            )
        )
        if chart is None:
            raise HTTPException(404, "Chart not found")

        run = db.scalar(
            select(ChartCalculationRun)
            .where(
                ChartCalculationRun.chart_id == chart.id,
                ChartCalculationRun.status == "complete",
                ChartCalculationRun.result.is_not(None),
            )
            .order_by(ChartCalculationRun.created_at.desc())
            .limit(1)
        )
        if run is None:
            return {
                "status": "unavailable",
                "system": "vedic",
                "profiles_checked": 2,
                "completed_chart_count": int(completed_chart_count),
                "chart_ids": selected_chart_ids,
                "score": None,
                "factors": [],
                "reason": "completed_chart_result_unavailable",
                "message": "A completed saved chart result could not be loaded.",
            }

        try:
            moon_longitude = extract_d1_lahiri_moon_longitude(chart, run)
        except CompatibilityChartError as exc:
            return {
                "status": "unavailable",
                "system": "vedic",
                "profiles_checked": 2,
                "completed_chart_count": int(completed_chart_count),
                "chart_ids": selected_chart_ids,
                "score": None,
                "factors": [],
                "reason": exc.reason,
                "message": exc.message,
            }

        run_records.append(run)
        moon_longitudes.append(moon_longitude)

    try:
        calculation = calculate_ashtakoota(moon_longitudes[0], moon_longitudes[1])
    except (TypeError, ValueError) as exc:
        logger.warning("Ashtakoota calculation rejected saved Moon data: %s", exc)
        return {
            "status": "unavailable",
            "system": "vedic",
            "profiles_checked": 2,
            "completed_chart_count": int(completed_chart_count),
            "chart_ids": selected_chart_ids,
            "score": None,
            "factors": [],
            "reason": "moon_longitude_invalid",
            "message": "The saved D1 Moon longitude data is invalid; no compatibility score was saved.",
        }

    report_result = {
        **calculation,
        "role_mapping": {
            "profile_a": "bride",
            "profile_b": "groom",
            "note": "Swap profile order to reverse traditional directional scoring roles.",
        },
        "chart_ids": selected_chart_ids,
        "calculation_run_ids": [str(run.id) for run in run_records],
    }
    report = CompatibilityReport(
        user_id=user.id,
        profile_a_id=payload.profile_a_id,
        profile_b_id=payload.profile_b_id,
        system="vedic",
        status="complete",
        result=report_result,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return {
        "status": "available",
        "system": "vedic",
        "profiles_checked": 2,
        "completed_chart_count": int(completed_chart_count),
        "chart_ids": selected_chart_ids,
        "report_id": str(report.id),
        "score": calculation["total_score"],
        "maximum_score": calculation["maximum_score"],
        "factors": calculation["factors"],
        "result": report_result,
        "reason": "ashtakoota_calculated",
        "message": (
            "Ashtakoota was calculated from saved Vedic D1 Lahiri Moon positions. "
            "Profile A is treated as bride and Profile B as groom for directional "
            "scoring. Bhakoot cancellation has not been evaluated."
        ),
    }




@router.get("/astrology/charts/{chart_id}", response_model=CalculationResultResponse)
def get_calculated_chart(chart_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    chart = db.scalar(select(BirthChart).join(BirthProfile, BirthProfile.id == BirthChart.profile_id).where(BirthChart.id == chart_id, BirthProfile.owner_id == user.id))
    if chart is None:
        raise HTTPException(404, "Chart not found")
    run = db.scalar(select(ChartCalculationRun).where(ChartCalculationRun.chart_id == chart.id).order_by(ChartCalculationRun.created_at.desc()))
    if run is None:
        raise HTTPException(404, "Chart calculation result not found")
    return _calculation_response(chart, run)


@router.get("/astrology/charts/{chart_id}/vedic-dignity", response_model=VedicDignityResponse)
def get_vedic_dignity(chart_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Analyze only the owner's already-saved Vedic D1 planetary longitudes."""
    chart = db.scalar(
        select(BirthChart)
        .join(BirthProfile, BirthProfile.id == BirthChart.profile_id)
        .where(BirthChart.id == chart_id, BirthProfile.owner_id == user.id)
    )
    if chart is None:
        raise HTTPException(404, "Chart not found")
    if chart.system != "vedic" or chart.division != "D1":
        raise HTTPException(422, "Planetary dignity analysis requires a saved Vedic D1 chart")
    if chart.status != "complete":
        raise HTTPException(409, "Planetary dignity is unavailable because this chart is not complete")
    run = db.scalar(
        select(ChartCalculationRun)
        .where(ChartCalculationRun.chart_id == chart.id)
        .order_by(ChartCalculationRun.created_at.desc())
    )
    if run is None or run.status != "complete" or not isinstance(run.result, dict):
        raise HTTPException(409, "Planetary dignity is unavailable because this chart has no completed result")
    try:
        return analyze_vedic_d1_dignity(run.result, chart_id=str(chart.id), profile_id=str(chart.profile_id))
    except DignityInputError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/astrology/charts", response_model=ChartHistoryPage)
def list_chart_history(
    profile_id: UUID | None = None,
    system: str | None = Query(default=None, pattern="^(vedic|western)$"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    owned_charts = (
        select(BirthChart.id, BirthChart.profile_id, BirthProfile.display_name.label("profile_name"),
               BirthChart.system, BirthChart.division, BirthChart.status, BirthChart.created_at,
               BirthChart.config.label("configuration"), BirthChart.unavailable_reason)
        .join(BirthProfile, BirthProfile.id == BirthChart.profile_id)
        .where(BirthProfile.owner_id == user.id)
    )
    if profile_id is not None:
        owned_charts = owned_charts.where(BirthChart.profile_id == profile_id)
    if system is not None:
        owned_charts = owned_charts.where(BirthChart.system == system)

    total = db.scalar(select(func.count()).select_from(owned_charts.subquery())) or 0
    rows = db.execute(
        owned_charts.order_by(BirthChart.created_at.desc(), BirthChart.id.desc())
        .offset(offset).limit(limit)
    ).mappings().all()
    return ChartHistoryPage(
        items=[ChartHistoryItem(**row) for row in rows], total=total, limit=limit, offset=offset
    )
