""" 应用配置从根目录读取环境变量，并暴露settings单里 """
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    app_name: str = "rag-knowledge"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag_kb"
    cos_secret_id: str = ""
    cos_secret_key: str = ""
    cos_region: str = ""
    cos_bucket: str = ""
    cors_origins: str = ""
    # Embedding模型
    ai_base_url: str = "http://127.0.0.1:8000"
    ai_api_key: str = ""
    embedding_model: str = "qwen3.7-text-embedding-flash"
    embedding_dim: int = 1024
    embedding_batch_size: int = 10

    # 文档上传与拆分
    upload_max_size_mb: int = 50
    chunk_size: int = 600
    chunk_overlap: int = 60

    @property
    def cos_configured(self) -> bool:
        return bool(self.cos_secret_id and self.cos_secret_key and self.cos_bucket)

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]



@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
