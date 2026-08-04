import asyncio
import json
import re
import secrets
import time
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.conversation import ConversationStore, expand_follow_up
from app.downloads import DOWNLOAD_SOURCE, download_answer
from app.guardrails import OFF_TOPIC, SYSTEM_PROMPT, fixed_answer, likely_in_domain
from app.intent_router import SemanticIntentRouter
from app.logger import log_exchange
from app.ollama import OllamaClient
from app.rag import KnowledgeBase
from app.rate_limit import rate_limiter
from app.schemas import ActionLink, ChatRequest, ChatResponse, HealthResponse, Source

ollama = OllamaClient()
kb = KnowledgeBase(ollama)
intent_router = SemanticIntentRouter(ollama)
conversations = ConversationStore()


async def resolve_download(message: str):
    result = download_answer(message)
    if result is not None:
        return result
    intent = await intent_router.download_intent(message)
    if intent is None:
        return None
    return download_answer(message, assume_download=True, platform_hint=intent.platform)


def answer_has_no_evidence(answer: str) -> bool:
    return bool(re.search(r"точн\w* ответ\w*.{0,35}(?:нет|не найден)|в базе знаний.{0,35}(?:нет|не найден)", answer, re.I))


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Требуется корректный X-Admin-Token")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.log_path.parent.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="Lime AI Support", version="1.0.0", lifespan=lifespan,
    description="Полностью локальный RAG-ассистент поддержки Lime HD TV",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=settings.origins != ["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Session-ID"],
)


@app.middleware("http")
async def disable_widget_cache(request: Request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/widget/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


app.mount("/widget", StaticFiles(directory="widget"), name="widget")


async def answer_request(body: ChatRequest) -> ChatResponse:
    started = time.perf_counter()
    message = " ".join(body.message.split())
    session_id = body.session_id or str(uuid.uuid4())
    previous_user = await conversations.last_user(session_id)
    resolved_message = expand_follow_up(message, previous_user)
    answer = fixed_answer(message)
    sources: list[Source] = []
    links: list[ActionLink] = []

    download = await resolve_download(resolved_message) if answer is None else None
    if download is not None:
        answer, actions = download
        links = [ActionLink(label=action.label, url=action.url) for action in actions]
        sources = [Source(question=DOWNLOAD_SOURCE.question, url=DOWNLOAD_SOURCE.url, relevance=1.0)]

    if answer is None and not likely_in_domain(resolved_message):
        answer = OFF_TOPIC

    if answer is None:
        hits = await kb.search(resolved_message)
        best = hits[0].relevance if hits else 0
        if not hits or best < settings.min_relevance:
            answer = "В базе знаний Lime HD TV нет точного ответа на этот вопрос. Пожалуйста, обратитесь в службу поддержки."
        else:
            sources = [Source(question=hits[0].question, url=hits[0].url, relevance=round(hits[0].relevance, 3))]
            if best >= settings.direct_answer_relevance:
                answer = hits[0].answer
            else:
                context = "\n\n".join(
                    f"FAQ {i + 1}\nВопрос: {h.question}\nОтвет: {h.answer}"
                    for i, h in enumerate(hits)
                )
                answer = await ollama.chat(
                    SYSTEM_PROMPT,
                    f"КОНТЕКСТ FAQ:\n{context}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{resolved_message}",
                )
                if answer_has_no_evidence(answer):
                    sources = []

    latency = round((time.perf_counter() - started) * 1000)
    await conversations.add(session_id, message, answer)
    await log_exchange(session_id=session_id, question=message, answer=answer, latency_ms=latency)
    return ChatResponse(answer=answer, session_id=session_id, sources=sources, links=links, latency_ms=latency)


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limiter)])
async def chat(body: ChatRequest) -> ChatResponse:
    try:
        return await answer_request(body)
    except httpx.ConnectError as exc:
        raise HTTPException(503, "Локальная AI-модель недоступна") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(504, "Локальная AI-модель не успела ответить") from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(503, "Локальные модели ещё не загружены. Дождитесь завершения model-init.") from exc
        raise HTTPException(502, "Локальная AI-модель вернула ошибку") from exc


@app.post("/chat/stream", dependencies=[Depends(rate_limiter)])
async def chat_stream(body: ChatRequest) -> StreamingResponse:
    def event(payload: dict) -> str:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def events():
        started = time.perf_counter()
        message = " ".join(body.message.split())
        session_id = body.session_id or str(uuid.uuid4())
        previous_user = await conversations.last_user(session_id)
        resolved_message = expand_follow_up(message, previous_user)
        sources: list[Source] = []
        links: list[ActionLink] = []
        answer = fixed_answer(message)
        model_user: str | None = None
        try:
            download = await resolve_download(resolved_message) if answer is None else None
            if download is not None:
                answer, actions = download
                links = [ActionLink(label=action.label, url=action.url) for action in actions]
                sources = [Source(question=DOWNLOAD_SOURCE.question, url=DOWNLOAD_SOURCE.url, relevance=1.0)]

            if answer is None and not likely_in_domain(resolved_message):
                answer = OFF_TOPIC

            if answer is None:
                hits = await kb.search(resolved_message)
                best = hits[0].relevance if hits else 0
                if not hits or best < settings.min_relevance:
                    answer = "В базе знаний Lime HD TV нет точного ответа на этот вопрос. Пожалуйста, обратитесь в службу поддержки."
                else:
                    relevant_hits = hits[:1]
                    sources = [
                        Source(question=hit.question, url=hit.url, relevance=round(hit.relevance, 3))
                        for hit in relevant_hits
                    ]
                    if best >= settings.direct_answer_relevance:
                        answer = hits[0].answer
                    else:
                        context = "\n\n".join(
                            f"FAQ {i + 1}\nВопрос: {hit.question}\nОтвет: {hit.answer}"
                            for i, hit in enumerate(hits)
                        )
                        model_user = f"КОНТЕКСТ FAQ:\n{context}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{resolved_message}"

            yield event({"type": "meta", "session_id": session_id})
            parts: list[str] = []
            if model_user is not None:
                async for chunk in ollama.chat_stream(SYSTEM_PROMPT, model_user):
                    parts.append(chunk)
                    yield event({"type": "chunk", "content": chunk})
                answer = "".join(parts).strip()
                if answer_has_no_evidence(answer):
                    sources = []
            else:
                for chunk in re.findall(r"\S+\s*|\s+", answer or ""):
                    parts.append(chunk)
                    yield event({"type": "chunk", "content": chunk})
                    await asyncio.sleep(0.012)

            if not answer:
                answer = "Не удалось сформировать ответ. Пожалуйста, попробуйте ещё раз."
            latency = round((time.perf_counter() - started) * 1000)
            await conversations.add(session_id, message, answer)
            await log_exchange(session_id=session_id, question=message, answer=answer, latency_ms=latency)
            yield event({
                "type": "done",
                "session_id": session_id,
                "sources": [source.model_dump() for source in sources],
                "links": [link.model_dump() for link in links],
                "latency_ms": latency,
            })
        except httpx.ConnectError:
            yield event({"type": "error", "detail": "Локальная AI-модель недоступна"})
        except httpx.TimeoutException:
            yield event({"type": "error", "detail": "Локальная AI-модель не успела ответить"})
        except Exception:
            yield event({"type": "error", "detail": "Не удалось получить ответ"})
    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    available = await ollama.available()
    models = await ollama.installed_models()
    chat_ready = settings.ollama_chat_model in models
    embed_ready = settings.ollama_embed_model in models
    return HealthResponse(
        status="ok" if available and chat_ready and embed_ready and kb.count else "degraded",
        model_available=available and chat_ready and embed_ready,
        chat_model_available=chat_ready,
        embedding_model_available=embed_ready,
        knowledge_items=kb.count,
    )


@app.post("/admin/reindex", dependencies=[Depends(rate_limiter), Depends(require_admin)])
async def reindex() -> dict[str, int]:
    try:
        return {"indexed": await kb.rebuild()}
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Не удалось создать embeddings") from exc


@app.get("/")
async def demo() -> FileResponse:
    return FileResponse("widget/demo.html")
