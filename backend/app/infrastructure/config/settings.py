"""
Application Settings and Configuration.

Responsible for:
- Managing API keys (stored in environment variables or secret management systems)
- Storing configuration values
- Supporting environment-specific settings (dev, staging, prod)

All configuration values should be accessed through this module.

Where `.env` is loaded:
- The FastAPI entry point ([backend/app/main.py](backend/app/main.py)) calls `load_dotenv()`.
- Additionally, Settings is configured with `env_file='.env'` to support scripts/tests that
    import settings without going through the FastAPI entry point.
"""
from dotenv import find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

def _default_cors_origins() -> str:
    # Comma-separated list.
    # This is the default for local development; override via env in staging/production.
    return "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000"

class Settings(BaseSettings):
    # `extra="ignore"` prevents crashes when unrelated env vars exist.
    model_config = SettingsConfigDict(
        # `.env` is located via search in the main.py file (supports running from repo root OR backend/).
        env_file=".env",
        extra="ignore",
    )

    # LLM routing
    # - auto: prefer OpenAI (OwlChat UI) when OPENAI_API_KEY is present, else Gemini when GEMINI_API_KEY is present
    # - openai: require OPENAI_API_KEY
    # - gemini/google: require GEMINI_API_KEY
    LLM_PROVIDER: str = Field(default="auto")

    # Gemini
    GEMINI_API_KEY: str | None = Field(default=None, env="GOOGLE_API_KEY")

    # Keep this as an example default; override via env if desired.
    DEFAULT_MODEL: str = Field(
        default="gemini-2.5-flash",
    )

    # OpenAI-compatible endpoints
    # NOTE: These are intended for OpenAI-compatible gateways (e.g. OwlChat/OpenUI),
    # not necessarily OpenAI itself.
    OPENAI_API_KEY: str | None = Field(default=None, env="OPENAI_API_KEY")

    # For OpenAI-compatible mode, set this to the gateway's OpenAI route.
    OPENAI_BASE_URL: str | None = Field(default=None, env="OPENAI_BASE_URL")
    OPENAI_MODEL: str = Field(default="gemini-2.5-flash")

    # Comma-separated list of allowed origins.
    CORS_ALLOW_ORIGINS: str = Field(
        default_factory=_default_cors_origins,
    )

settings = Settings()
