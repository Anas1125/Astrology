import json
from pathlib import Path

from app.core.config import Settings
from app.db.base import normalize_database_url
from app.services.astrology.sweph import resolve_ephemeris_path, resolve_native_library_path


def test_relative_ephemeris_path_is_resolved_from_backend_root():
    backend_root = Path(__file__).resolve().parents[1]
    assert resolve_ephemeris_path("ephe") == (backend_root / "ephe").resolve()


def test_relative_native_library_path_is_resolved_from_backend_root():
    backend_root = Path(__file__).resolve().parents[1]
    assert resolve_native_library_path("native/linux-x64/libastroai-swe.so") == (
        backend_root / "native/linux-x64/libastroai-swe.so"
    ).resolve()


def test_neon_prisma_url_is_used_when_database_url_is_missing(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_PRISMA_URL", "postgresql://astro:test@neon.example/db?sslmode=require")

    config = Settings(_env_file=None)

    assert config.database_url == "postgresql://astro:test@neon.example/db?sslmode=require"


def test_explicit_database_url_takes_precedence_over_neon_prisma_url(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://primary.example/db")
    monkeypatch.setenv("POSTGRES_PRISMA_URL", "postgresql://pooled.example/db")

    config = Settings(_env_file=None)

    assert config.database_url == "postgresql://primary.example/db"



def test_neon_prisma_url_removes_prisma_only_pgbouncer_query():
    url = normalize_database_url(
        "postgresql://astro:secret@ep-example-pooler.neon.tech/db?sslmode=require&pgbouncer=true&connect_timeout=15"
    )

    assert url.drivername == "postgresql+psycopg"
    assert "pgbouncer" not in url.query
    assert url.query["sslmode"] == "require"
    assert url.query["connect_timeout"] == "15"

def test_vercel_config_includes_ephemeris_files():
    backend_root = Path(__file__).resolve().parents[1]

    config = json.loads(
        (backend_root / "vercel.json").read_text(encoding="utf-8")
    )

    function_config = config["functions"]["app/main.py"]

    assert function_config["includeFiles"] == "{ephe/*.se1,native/linux-x64/libastroai-swe.so}"
    assert (backend_root / "ephe/sepl_18.se1").is_file()
    assert (backend_root / "ephe/semo_18.se1").is_file()
    assert (backend_root / "native/linux-x64/libastroai-swe.so").is_file()