from datetime import date, datetime, time
import math
from typing import Literal
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from app.services.ai.contracts import IntelligenceResponse


def validate_iana_timezone(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip()
    try:
        ZoneInfo(normalized)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError("Enter a valid IANA timezone identifier") from exc
    return normalized


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class PasswordResetRequest(BaseModel):
    token: str = Field(min_length=32, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class PasswordResetRequestResponse(BaseModel):
    message: str


class PasswordResetResponse(BaseModel):
    message: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AccountResponse(BaseModel):
    id: UUID
    email: EmailStr
    role: str


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    relationship: Literal["self", "father", "mother", "spouse_partner", "son_daughter", "brother_sister", "family_member", "friend", "other"] = "self"
    birth_date: date
    birth_time: time | None = None
    time_accuracy: Literal["exact", "approximate", "unknown"] = "unknown"
    birthplace: str = Field(min_length=1, max_length=200)
    country: str = Field(default="", max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=80)

    @field_validator("display_name", "birthplace")
    @classmethod
    def trim_required_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        return validate_iana_timezone(value)

    @model_validator(mode="after")
    def validate_birth_details(self):
        if self.birth_date > date.today():
            raise ValueError("Birth date cannot be in the future")
        if self.time_accuracy == "exact" and self.birth_time is None:
            raise ValueError("An exact birth time is required when time accuracy is exact")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        return self


class ProfileResponse(ProfileCreate):
    model_config = ConfigDict(from_attributes=True)
    id: UUID


class LocationSuggestion(BaseModel):
    id: str
    city: str
    region: str | None = None
    country: str
    latitude: float
    longitude: float
    timezone: str | None = None
    attribution: str


class ProfilePatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    relationship: Literal["self", "father", "mother", "spouse_partner", "son_daughter", "brother_sister", "family_member", "friend", "other"] | None = None
    birth_date: date | None = None
    birth_time: time | None = None
    time_accuracy: Literal["exact", "approximate", "unknown"] | None = None
    birthplace: str | None = Field(default=None, min_length=1, max_length=200)
    country: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=80)

    @field_validator("display_name", "birthplace")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("This field cannot be blank")
        return normalized

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        return validate_iana_timezone(value)

    @model_validator(mode="after")
    def validate_patch_details(self):
        if self.birth_date is not None and self.birth_date > date.today():
            raise ValueError("Birth date cannot be in the future")
        if self.time_accuracy == "exact" and self.birth_time is None:
            raise ValueError("Provide the exact birth time when setting time accuracy to exact")
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together")
        return self


class ChartCreate(BaseModel):
    profile_id: UUID
    system: str = Field(pattern="^(vedic|western)$")
    division: str = "D1"


class ChartResponse(BaseModel):
    id: UUID
    profile_id: UUID
    system: str
    division: str
    status: str
    unavailable_reason: str


class AstrologyChartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: UUID
    house_system: Literal["P", "W", "K", "R", "C", "E", "O", "B", "M", "A", "V", "X", "H", "T"] = "P"
    aspect_orbs: dict[str, float] | None = None

    @field_validator("aspect_orbs")
    @classmethod
    def validate_aspect_orbs(cls, value: dict[str, float] | None):
        if value is None:
            return None
        allowed = {"conjunction", "sextile", "square", "trine", "opposition"}
        if set(value) - allowed or any(not math.isfinite(orb) or orb < 0 or orb > 15 for orb in value.values()):
            raise ValueError("Aspect orbs must use supported aspects with values between 0 and 15 degrees")
        return value


class VedicChartRequest(AstrologyChartRequest):
    division: Literal["D1", "D9"] = "D1"
    dasha_year_convention: Literal["savana_360_day"] = "savana_360_day"


class CalculationResultResponse(BaseModel):
    chart_id: UUID
    calculation_run_id: UUID
    profile_id: UUID
    calculation_system: str
    status: str
    engine_version: str | None
    ephemeris_version: str | None
    configuration: dict
    input_snapshot: dict | None
    result: dict | None
    calculated_at: datetime


class VedicDignityResponse(BaseModel):
    status: Literal["provisional"]
    chart_id: UUID
    profile_id: UUID
    astrology_system: Literal["vedic"]
    division: Literal["D1"]
    zodiac: Literal["sidereal"]
    ayanamsa: str
    ruleset_id: str
    ruleset_version: str
    source_id: str
    source_ids: list[str]
    source_references: list[dict]
    source_status: str
    source_locator: str
    methodology_note: str
    shadbala: dict
    planets: list[dict]
    excluded_planets: list[str]


class PanchangRequest(BaseModel):
    local_date: date
    location_name: str = Field(min_length=1, max_length=160)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str = Field(min_length=1, max_length=80)

    @field_validator("location_name")
    @classmethod
    def validate_location_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Location name cannot be blank")
        return value.strip()

    @field_validator("timezone")
    @classmethod
    def validate_panchang_timezone(cls, value: str) -> str:
        normalized = validate_iana_timezone(value)
        if normalized is None:
            raise ValueError("An IANA timezone is required")
        return normalized


class HoroscopeRequest(BaseModel):
    mode: Literal["general", "personalized"] = "general"
    system: Literal["vedic", "western"]
    local_date: date
    period: Literal["daily", "weekly", "monthly"] = "daily"
    category: Literal["overview", "career", "relationships", "finance", "personal_growth"] = "overview"
    language: Literal["en", "ta"] = "en"
    sign: str | None = Field(default=None, min_length=1, max_length=40)
    profile_id: UUID | None = None
    chart_id: UUID | None = None

    @model_validator(mode="after")
    def mode_requirements(self):
        if self.mode == "general" and not self.sign:
            raise ValueError("Choose a sign for a general horoscope")
        if self.mode == "personalized" and self.profile_id is None:
            raise ValueError("Choose a birth profile for a personalized horoscope")
        return self


class HoroscopeAvailabilityResponse(BaseModel):
    status: Literal["available", "unavailable", "missing_chart"]
    mode: Literal["general", "personalized"]
    system: Literal["vedic", "western"]
    local_date: date
    period: Literal["daily", "weekly", "monthly"]
    category: Literal["overview", "career", "relationships", "finance", "personal_growth"]
    sign: str | None
    chart_id: str | None
    content: str | None
    source_references: list[dict | str]
    reason: str
    message: str


class CompatibilityRequest(BaseModel):
    profile_a_id: UUID
    profile_b_id: UUID
    system: Literal["vedic", "western"]
    chart_a_id: UUID | None = None
    chart_b_id: UUID | None = None

    @model_validator(mode="after")
    def profiles_must_differ(self):
        if self.profile_a_id == self.profile_b_id:
            raise ValueError("Choose two different birth profiles")
        if (self.chart_a_id is None) != (self.chart_b_id is None):
            raise ValueError("Choose a saved chart for both profiles or neither")
        return self


class ChartHistoryItem(BaseModel):
    id: UUID
    profile_id: UUID
    profile_name: str
    system: Literal["vedic", "western"]
    division: str
    status: str
    created_at: datetime
    configuration: dict
    unavailable_reason: str | None = None


class ChartHistoryPage(BaseModel):
    items: list[ChartHistoryItem]
    total: int
    limit: int
    offset: int


class AIConversationCreate(BaseModel):
    profile_id: UUID
    chart_id: UUID | None = None
    astrology_system: Literal["vedic", "western"]
    language: Literal["en", "ta"] = "en"
    title: str = Field(default="New conversation", min_length=1, max_length=160)


class AIMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=4000)

    @field_validator("content")
    @classmethod
    def trim_message(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Message cannot be blank")
        return normalized


class AIMessageResponse(BaseModel):
    id: UUID
    role: Literal["user", "assistant"]
    content: str
    structured_response: IntelligenceResponse | None = None
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    input_tokens: int
    output_tokens: int
    created_at: datetime


class AIChatResponse(BaseModel):
    message: AIMessageResponse


class AIConversationResponse(BaseModel):
    id: UUID
    profile_id: UUID | None
    profile_name: str | None = None
    chart_id: UUID | None
    astrology_system: Literal["vedic", "western"]
    language: Literal["en", "ta"]
    title: str
    created_at: datetime
    updated_at: datetime


class AIConversationHistory(AIConversationResponse):
    messages: list[AIMessageResponse]


class AIConversationList(BaseModel):
    items: list[AIConversationResponse]
    total: int
