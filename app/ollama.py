import asyncio
import json
import time
from collections.abc import AsyncIterator

import httpx

from app.config import settings
from app.guardrails import SYSTEM_PROMPT
from app.logger import logger


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_url.rstrip("/")
        self._client: httpx.AsyncClient | None = None
        self._lock = asyncio.Lock()

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        timeout=120,
                        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
                    )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        t0 = time.perf_counter()
        logger.info(f"[Ollama] Requesting embeddings for {len(texts)} item(s) using {settings.ollama_embed_model}...")
        try:
            client = await self.get_client()
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": texts},
            )
            response.raise_for_status()
            res = response.json()["embeddings"]
            logger.info(f"[Ollama] Embeddings completed in {round((time.perf_counter() - t0) * 1000)}ms")
            return res
        except Exception as exc:
            logger.error(f"[Ollama] Embeddings failed after {round((time.perf_counter() - t0) * 1000)}ms: {exc}")
            raise

    async def chat(self, system: str = SYSTEM_PROMPT, user: str = "") -> str:
        t0 = time.perf_counter()
        logger.info(f"[Ollama] Starting chat completion using {settings.ollama_chat_model}...")
        try:
            client = await self.get_client()
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": settings.ollama_chat_model,
                    "stream": False,
                    "think": False,
                    "keep_alive": "10m",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "options": {"temperature": 0.1, "num_predict": 300},
                },
            )
            response.raise_for_status()
            res = response.json()["message"]["content"].strip()
            logger.info(f"[Ollama] Chat completion finished in {round((time.perf_counter() - t0) * 1000)}ms")
            return res
        except Exception as exc:
            logger.error(f"[Ollama] Chat completion failed after {round((time.perf_counter() - t0) * 1000)}ms: {exc}")
            raise

    async def chat_stream(self, system: str = SYSTEM_PROMPT, user: str = "") -> AsyncIterator[str]:
        t0 = time.perf_counter()
        logger.info(f"[Ollama] Starting chat stream using {settings.ollama_chat_model}...")
        try:
            client = await self.get_client()
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": settings.ollama_chat_model,
                    "stream": True,
                    "think": False,
                    "keep_alive": "10m",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "options": {"temperature": 0.1, "num_predict": 300},
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    payload = json.loads(line)
                    if payload.get("error"):
                        raise RuntimeError(payload["error"])
                    content = payload.get("message", {}).get("content", "")
                    if content:
                        yield content
            logger.info(f"[Ollama] Chat stream finished in {round((time.perf_counter() - t0) * 1000)}ms")
        except Exception as exc:
            logger.error(f"[Ollama] Chat stream failed after {round((time.perf_counter() - t0) * 1000)}ms: {exc}")
            raise

    async def faq_route(self, question: str, faq_question: str, faq_answer: str) -> str:
        t0 = time.perf_counter()
        clean_question = question.replace("---", "-").replace("===", "=").replace("```", "'''")
        system = (
            f"{SYSTEM_PROMPT}\n\n"
            "Распредели вопрос пользователя ровно в одну категорию.\n"
            "MATCH — статья FAQ помогает решить описанную ситуацию, включая синонимы, "
            "разговорные формулировки и условные решения.\n"
            "SUPPORT — вопрос относится к Lime HD TV, приложению, каналам, аккаунту, оплате, "
            "подписке или настройкам, но данная статья не даёт подходящего решения.\n"
            "OFFTOPIC — вопрос не относится к сервису Lime HD TV, например вычисления, погода, "
            "написание кода или общие знания.\n"
            "Ответь только MATCH, SUPPORT или OFFTOPIC."
        )
        user = f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{clean_question}\n\nСТАТЬЯ FAQ:\n{faq_question}\n{faq_answer}"
        logger.info(f"[RAG Route] Checking candidate FAQ: '{faq_question[:50]}...' for question: '{question[:50]}...'")
        try:
            client = await self.get_client()
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": settings.ollama_chat_model,
                    "stream": False,
                    "think": False,
                    "keep_alive": "10m",
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "options": {"temperature": 0, "num_predict": 5},
                },
            )
            response.raise_for_status()
            answer = response.json()["message"]["content"].strip().upper()
            route = "SUPPORT"
            for r in ("MATCH", "SUPPORT", "OFFTOPIC"):
                if r in answer:
                    route = r
                    break
            logger.info(f"[RAG Route] Candidate '{faq_question[:50]}...' -> {route} ({round((time.perf_counter() - t0) * 1000)}ms)")
            return route
        except Exception as exc:
            logger.error(f"[RAG Route] Ollama call failed for candidate '{faq_question[:50]}...': {exc}")
            raise

    async def available(self) -> bool:
        try:
            client = await self.get_client()
            return (await client.get(f"{self.base_url}/api/tags")).is_success
        except httpx.HTTPError as exc:
            logger.warning(f"[Ollama Health] /api/tags check failed: {exc}")
            return False

    async def installed_models(self) -> set[str]:
        try:
            client = await self.get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            names = {item["name"] for item in response.json().get("models", [])}
            return names | {name.removesuffix(":latest") for name in names}
        except httpx.HTTPError as exc:
            logger.warning(f"[Ollama Health] Failed to fetch installed models: {exc}")
            return set()
