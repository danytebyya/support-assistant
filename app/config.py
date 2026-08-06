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
    min_relevance: float = 0.36
    direct_answer_relevance: float = 0.68
    admin_token: str = "change-this-before-production"
    trust_proxy: bool = False

    @property
    def origins(self) -> list[str]:
        return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

    def safe_path(self, path: Path) -> Path:
        base_dir = Path(__file__).resolve().parent.parent
        resolved = (base_dir / path).resolve() if not path.is_absolute() else path.resolve()
        try:
            resolved.relative_to(base_dir)
        except ValueError:
            raise ValueError(f"Path '{path}' escapes the allowed application base directory '{base_dir}'")
        return resolved

    @property
    def safe_chroma_path(self) -> Path:
        return self.safe_path(self.chroma_path)

    @property
    def safe_knowledge_path(self) -> Path:
        return self.safe_path(self.knowledge_path)

    @property
    def safe_log_path(self) -> Path:
        return self.safe_path(self.log_path)


settings = Settings()
