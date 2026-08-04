from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    session_id: str | None = Field(default=None, max_length=80)


class Source(BaseModel):
    question: str
    url: str
    relevance: float


class ActionLink(BaseModel):
    label: str
    url: str


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[Source] = Field(default_factory=list)
    links: list[ActionLink] = Field(default_factory=list)
    latency_ms: int


class HealthResponse(BaseModel):
    status: str
    model_available: bool
    chat_model_available: bool
    embedding_model_available: bool
    knowledge_items: int
