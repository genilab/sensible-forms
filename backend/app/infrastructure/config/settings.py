"""
Application Settings and Configuration.

Responsible for:
- Loading environment variables
- Managing API keys (stored in environment variables or secret management systems)
- Storing configuration values
- Supporting environment-specific settings (dev, staging, prod)

All configuration values should be accessed through this module.
"""
# Example Code:
from pathlib import Path

from dotenv import load_dotenv
from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _load_dotenv_candidates() -> None:
    """
    Load .env from common locations.
    """

    this_file = Path(__file__).resolve()
    backend_dir = this_file.parents[3]  # .../backend
    repo_root = this_file.parents[4]    # .../<repo root>

    for env_path in (repo_root / ".env", backend_dir / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


_load_dotenv_candidates()

def _default_cors_origins() -> str:
    # Comma-separated list.
    return "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"


class Settings(BaseSettings):
    # `extra="ignore"` prevents crashes when unrelated env vars exist.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Leave empty for local development; GeminiClient will raise a helpful
    # error at call-time if you attempt to use Gemini without configuring it.
    GEMINI_API_KEY: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "google_api_key",
        ),
    )

    # Keep this as an example default; override via env if desired.
    DEFAULT_MODEL: str = Field(
        default="gemini-2.5-flash",
        validation_alias=AliasChoices("DEFAULT_MODEL", "default_model"),
    )

    # Comma-separated list of allowed origins.
    CORS_ALLOW_ORIGINS: str = Field(
        default_factory=_default_cors_origins,
        validation_alias=AliasChoices("CORS_ALLOW_ORIGINS", "cors_allow_origins"),
    )

settings = Settings()
