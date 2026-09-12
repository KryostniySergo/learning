# app/config.py
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.example", env_prefix="APP_", extra="ignore")

    # данные
    source_path: Path = Path("data/raw/constitution.txt")
    revision: str = "1993-12-12 (ред. 2020)"

    # векторное хранилище
    chroma_path: Path = Path("data/chroma")
    collection_name: str = "constitution_e5_small_v1"

    # эмбеддинги
    embedding_model: str = "intfloat/multilingual-e5-small"
    embedding_device: str = "cpu"

    # чанкование
    min_chunk_chars: int = 200
    max_chunk_chars: int = 900

    # поиск
    default_k: int = 5
    candidate_k: int = 30  # сколько достаём до реранкинга/фьюжена
    min_score: float = 0.80  # порог отсечения, подбирается по eval!
    use_hybrid: bool = True

    # LLM (опционально)
    llm_enabled: bool = False
    llm_base_url: str | None = None  # напр. http://localhost:11434/v1
    llm_api_key: str = "not-needed"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_timeout: float = 30.0
    llm_max_tokens: int = 500


settings = Settings()
