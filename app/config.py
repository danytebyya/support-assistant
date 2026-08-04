from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_url: str = "http://localhost:11434"
    ollama_chat_model: str = "qwen3:8b"
    ollama_embed_model: str = "qwen3-embedding:0.6b"
    chroma_path: Path = Path("data/chroma")
    knowledge_path: Path = Path("data/knowledge/faq.json")
    log_path: Path = Path("data/logs/chat.jsonl")
    allowed_origins: str = "*"
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60
    max_message_length: int = 1000
    top_k: int = 4
    min_relevance: float = 0.24
    direct_answer_relevance: float = 0.65
    admin_token: str = "change-this-before-production"

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]


settings = Settings()
