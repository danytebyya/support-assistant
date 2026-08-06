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
from app.downloads import (
    DOWNLOAD_SOURCE,
    detect_platform,
    download_answer,
    is_download_platform_follow_up,
)
from app.guardrails import OFF_TOPIC, fixed_answer, likely_in_domain
from app.logger import log_exchange, logger
from app.ollama import OllamaClient
from app.rag import KnowledgeBase
from app.rate_limit import rate_limiter
from app.schemas import ActionLink, ChatRequest, ChatResponse, HealthResponse, Source

ollama = OllamaClient()
kb = KnowledgeBase(ollama)
conversations = ConversationStore()
NO_EXACT_ANSWER = (
    "В базе знаний Lime HD TV нет точного ответа на этот вопрос. "
    "Напишите в службу поддержки: support@limehd.tv."
)


async def resolve_download(message: str, latest_message: str):
    result = download_answer(latest_message)
    if result is not None:
        return result
    if message != latest_message and is_download_platform_follow_up(latest_message):
        return download_answer(
            latest_message,
            assume_download=True,
            platform_hint=detect_platform(latest_message),
        )
    return None


async def resolve_knowledge(message: str, raw_message: str | None = None) -> tuple[str, list[Source]]:
    query = raw_message or message
    logger.info(f"[RAG] Searching knowledge base for query: '{query[:60]}...'")
    hits = await kb.search(query)
    if not hits and raw_message and raw_message != message:
        logger.info(f"[RAG] Retry search with expanded message: '{message[:60]}...'")
        hits = await kb.search(message)
    if not hits:
        logger.info("[RAG] No hits found in vector database.")
        return NO_EXACT_ANSWER, []

    top = hits[0]
    logger.info(f"[RAG] Top hit: '{top.question[:50]}...' with relevance {top.relevance:.3f} (threshold: {settings.direct_answer_relevance})")
    if top.relevance >= settings.direct_answer_relevance:
        logger.info(f"[RAG] Direct match found: '{top.question[:50]}...'")
        source = Source(question=top.question, url=top.url, relevance=round(top.relevance, 3))
        return top.answer, [source]

    valid_hits = [h for h in hits if h.relevance >= settings.min_relevance]
    if not valid_hits:
        logger.info(f"[RAG] All hits below min_relevance ({settings.min_relevance}).")
        if likely_in_domain(message):
            return NO_EXACT_ANSWER, []
        return OFF_TOPIC, []

    logger.info(f"[RAG] Evaluating up to 2 candidate(s) via Ollama faq_route...")
    saw_support = False
    for candidate in valid_hits[:2]:
        route = await ollama.faq_route(message, candidate.question, candidate.answer)
        if route == "MATCH":
            logger.info(f"[RAG] Candidate MATCH: '{candidate.question[:50]}...'")
            source = Source(
                question=candidate.question,
                url=candidate.url,
                relevance=round(candidate.relevance, 3),
            )
            return candidate.answer, [source]
        saw_support = saw_support or route == "SUPPORT"

    if saw_support or likely_in_domain(message):
        logger.info("[RAG] No exact MATCH found. Decision: NO_EXACT_ANSWER")
        return NO_EXACT_ANSWER, []
    logger.info("[RAG] Decision: OFF_TOPIC")
    return OFF_TOPIC, []


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if settings.admin_token == "change-this-before-production":
        logger.warning("SECURITY WARNING: Using default ADMIN_TOKEN!")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(401, "Требуется корректный X-Admin-Token")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.safe_log_path.parent.mkdir(parents=True, exist_ok=True)
    yield
    await ollama.close()


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
async def apply_security_headers_and_cache(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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
    logger.info(f"[Chat] Processing request from session {session_id[:8]}...: '{message[:60]}...'")
    previous_user = await conversations.last_user(session_id)
    resolved_message = expand_follow_up(message, previous_user)
    answer = fixed_answer(message)
    sources: list[Source] = []
    links: list[ActionLink] = []

    if answer is not None:
        logger.info(f"[Chat] Matched fixed answer rule for session {session_id[:8]}")

    download = await resolve_download(resolved_message, message) if answer is None else None
    if download is not None:
        logger.info(f"[Chat] Matched download rule for session {session_id[:8]}")
        answer, actions = download
        links = [ActionLink(label=action.label, url=action.url) for action in actions]
        sources = [Source(question=DOWNLOAD_SOURCE.question, url=DOWNLOAD_SOURCE.url, relevance=1.0)]

    if answer is None:
        answer, sources = await resolve_knowledge(resolved_message, raw_message=message)

    latency = round((time.perf_counter() - started) * 1000)
    logger.info(f"[Chat] Request session {session_id[:8]} completed in {latency}ms")
    await conversations.add(session_id, message, answer, context=resolved_message)
    await log_exchange(session_id=session_id, question=message, answer=answer, latency_ms=latency)
    return ChatResponse(answer=answer, session_id=session_id, sources=sources, links=links, latency_ms=latency)


@app.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limiter)])
async def chat(body: ChatRequest) -> ChatResponse:
    try:
        return await answer_request(body)
    except httpx.ConnectError as exc:
        logger.error(f"[Chat 503] ConnectError to Ollama ({settings.ollama_url}): {exc}")
        raise HTTPException(503, "Локальная AI-модель недоступна") from exc
    except httpx.TimeoutException as exc:
        logger.error(f"[Chat 504] TimeoutException waiting for Ollama: {exc}")
        raise HTTPException(504, "Локальная AI-модель не успела ответить") from exc
    except httpx.HTTPStatusError as exc:
        logger.error(f"[Chat {exc.response.status_code}] HTTPStatusError from Ollama: {exc}")
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

        logger.info(f"[Stream] Starting SSE stream for session {session_id[:8]}...: '{message[:60]}...'")
        yield event({"type": "meta", "session_id": session_id})

        previous_user = await conversations.last_user(session_id)
        resolved_message = expand_follow_up(message, previous_user)
        sources: list[Source] = []
        links: list[ActionLink] = []
        answer = fixed_answer(message)
        try:
            download = await resolve_download(resolved_message, message) if answer is None else None
            if download is not None:
                logger.info(f"[Stream] Download rule matched for session {session_id[:8]}")
                answer, actions = download
                links = [ActionLink(label=action.label, url=action.url) for action in actions]
                sources = [Source(question=DOWNLOAD_SOURCE.question, url=DOWNLOAD_SOURCE.url, relevance=1.0)]

            if answer is None:
                answer, sources = await resolve_knowledge(resolved_message, raw_message=message)

            parts: list[str] = []
            for chunk in re.findall(r"\S+\s*|\s+", answer or ""):
                parts.append(chunk)
                yield event({"type": "chunk", "content": chunk})
                await asyncio.sleep(0.012)

            if not answer:
                answer = "Не удалось сформировать ответ. Пожалуйста, попробуйте ещё раз."
            latency = round((time.perf_counter() - started) * 1000)
            logger.info(f"[Stream] SSE stream finished for session {session_id[:8]} in {latency}ms")
            await conversations.add(session_id, message, answer, context=resolved_message)
            await log_exchange(session_id=session_id, question=message, answer=answer, latency_ms=latency)
            yield event({
                "type": "done",
                "session_id": session_id,
                "sources": [source.model_dump() for source in sources],
                "links": [link.model_dump() for link in links],
                "latency_ms": latency,
            })
        except httpx.ConnectError as exc:
            logger.error(f"[Stream] ConnectError to Ollama for session {session_id[:8]}: {exc}")
            yield event({"type": "error", "detail": "Локальная AI-модель недоступна"})
        except httpx.TimeoutException as exc:
            logger.error(f"[Stream] TimeoutException from Ollama for session {session_id[:8]}: {exc}")
            yield event({"type": "error", "detail": "Локальная AI-модель не успела ответить"})
        except Exception as e:
            logger.error(f"[Stream] Unhandled exception in chat_stream for session {session_id[:8]}: {e}", exc_info=True)
            yield event({"type": "error", "detail": f"Ошибка сервера: {str(e)}"})
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
