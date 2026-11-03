from uuid import UUID
from datetime import datetime, timezone
import hashlib
import json
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.base import get_db
from app.models.entities import BirthChart, BirthProfile, ChartCalculationRun, User
from app.schemas.api import AccountResponse, AstrologyChartRequest, VedicChartRequest, CalculationResultResponse, ChartCreate, ChartResponse, ChartHistoryItem, ChartHistoryPage, ProfileCreate, ProfilePatch, ProfileResponse, RegisterRequest, TokenResponse
from app.services.astrology import EngineUnavailable, VedicAstrologyEngine, WesternAstrologyEngine
from app.services.astrology.vedic import VEDIC_ENGINE_VERSION
from app.services.astrology.western import DEFAULT_ASPECT_ORBS, WESTERN_ENGINE_VERSION
from app.services.astrology.sweph import ENGINE_VERSION, InvalidBirthData

router = APIRouter()
oauth = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
CALCULATION_UNAVAILABLE_DETAIL = "Astrology calculation is unavailable under current server settings. No result was saved."


def current_user(token: str = Depends(oauth), db: Session = Depends(get_db)) -> User:
    try:
        uid = jwt.decode(token, settings.secret_key, algorithms=["HS256"])["sub"]
        user = db.get(User, UUID(uid))
    except (jwt.PyJWTError, ValueError, KeyError):
        user = None
    if user is None or not user.is_active:
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
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.post("/auth/login", response_model=TokenResponse)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == form_data.username))
    if not user or not user.is_active or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect")
    return TokenResponse(access_token=create_access_token(str(user.id)))


@router.get("/auth/me", response_model=AccountResponse)
def get_current_account(user: User = Depends(current_user)):
    return AccountResponse(id=user.id, email=user.email, role=user.role)


@router.get("/profiles", response_model=list[ProfileResponse])
def list_profiles(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return list(db.scalars(select(BirthProfile).where(BirthProfile.owner_id == user.id).order_by(BirthProfile.created_at.desc())))


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
    if profile.birth_time is None or profile.time_accuracy == "unknown":
        raise HTTPException(422, "A known birth time is required for houses and angles")
    if profile.latitude is None or profile.longitude is None:
        raise HTTPException(422, "Birth latitude and longitude are required")
    engine = VedicAstrologyEngine() if system == "vedic" else WesternAstrologyEngine()
    division = payload.division if system == "vedic" else "D1"
    try:
        provider = engine.get_provider()
    except EngineUnavailable as exc:
        raise HTTPException(503, CALCULATION_UNAVAILABLE_DETAIL) from exc
    calculation_config = {"house_system": payload.house_system}
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
        raise HTTPException(503, CALCULATION_UNAVAILABLE_DETAIL) from exc
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
        timezone_assumption=f"{profile.timezone}: local wall time converted using system IANA timezone data",
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


@router.get("/astrology/charts/{chart_id}", response_model=CalculationResultResponse)
def get_calculated_chart(chart_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    chart = db.scalar(select(BirthChart).join(BirthProfile, BirthProfile.id == BirthChart.profile_id).where(BirthChart.id == chart_id, BirthProfile.owner_id == user.id))
    if chart is None:
        raise HTTPException(404, "Chart not found")
    run = db.scalar(select(ChartCalculationRun).where(ChartCalculationRun.chart_id == chart.id).order_by(ChartCalculationRun.created_at.desc()))
    if run is None:
        raise HTTPException(404, "Chart calculation result not found")
    return _calculation_response(chart, run)


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
