from pydantic import AnyHttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


settings_config = SettingsConfigDict(
    env_file=".env",
    env_file_encoding="utf-8",
    case_sensitive=False,
)


class _Settings(BaseSettings):
    model_config = settings_config

    mysql_host: str
    mysql_port: int = 3306
    mysql_user: str
    mysql_password: str
    mysql_database: str

    qdrant_url: AnyHttpUrl = "http://localhost:6333"

    ollama_base_url: AnyHttpUrl = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    llm_model: str = "qwen2.5:1.5b"

    redis_url: str = "redis://localhost:6379/0"

    db_path: str = "data/metadata.db"


_instance = _Settings()

MYSQL_HOST = _instance.mysql_host
MYSQL_PORT = _instance.mysql_port
MYSQL_USER = _instance.mysql_user
MYSQL_PASSWORD = _instance.mysql_password
MYSQL_DATABASE = _instance.mysql_database

QDRANT_URL = str(_instance.qdrant_url)
OLLAMA_BASE_URL = str(_instance.ollama_base_url)
EMBEDDING_MODEL = _instance.embedding_model
LLM_MODEL = _instance.llm_model

REDIS_URL = _instance.redis_url
DB_PATH = _instance.db_path