"""Configuración de la aplicación (pydantic-settings, leída de variables de entorno)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM (Qware, OpenAI-compatible)
    llm_endpoint: str = "https://api.qware.me/v1"
    llm_model: str = "gemini-3-flash-agent"
    llm_api_key: str = ""
    llm_rate_limit_rpm: int = 50
    llm_timeout_segundos: int = 30
    llm_temperatura: float = 0.1
    llm_max_tokens: int = 600

    # Embeddings locales
    embedding_model: str = "paraphrase-multilingual-MiniLM-L12-v2"
    embedding_dim: int = 384

    # PostgreSQL
    postgres_user: str = "clasifica"
    postgres_password: str = "clasifica"
    postgres_db: str = "clasifica"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # App
    secret_key: str = "dev-secret-change-me"
    data_dir: str = "/var/clasifica/data"
    admin_username: str = "admin"
    admin_password: str = "admin"
    cors_origins: str = "http://localhost:8080,http://localhost:5173"

    # Workers
    celery_workers: int = 4
    celery_batch_workers: int = 2

    # Umbral de confianza para clasificación automática
    umbral_confianza: float = 0.70

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
