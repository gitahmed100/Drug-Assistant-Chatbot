from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ folder (this file lives in backend/app/core/config.py)
BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """All settings come from environment variables or the backend/.env file."""

    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"
    vector_store_dir: str = str(BASE_DIR / "data" / "vector_store")
    top_k: int = 4
    min_score: float = 0.25
    allowed_origins: str = "http://localhost:8501,http://localhost:7860"
    log_level: str = "INFO"

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


settings = Settings()
