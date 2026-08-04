import json
from collections.abc import AsyncIterator

import httpx

from app.config import settings


class OllamaClient:
    def __init__(self) -> None:
        self.base_url = settings.ollama_url.rstrip("/")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": texts},
            )
            response.raise_for_status()
            return response.json()["embeddings"]

    async def chat(self, system: str, user: str) -> str:
        async with httpx.AsyncClient(timeout=60) as client:
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
            return response.json()["message"]["content"].strip()

    async def chat_stream(self, system: str, user: str) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60) as client:
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

    async def faq_route(self, question: str, faq_question: str, faq_answer: str) -> str:
        system = (
            "Распредели вопрос пользователя ровно в одну категорию. "
            "MATCH — статья FAQ помогает решить описанную ситуацию, включая синонимы, "
            "разговорные формулировки и условные решения. "
            "SUPPORT — вопрос относится к Lime HD TV, приложению, каналам, аккаунту, оплате, "
            "подписке или настройкам, но данная статья не даёт подходящего решения. "
            "OFFTOPIC — вопрос не относится к сервису Lime HD TV, например вычисления, погода, "
            "написание кода или общие знания. "
            "Ответь только MATCH, SUPPORT или OFFTOPIC."
        )
        user = f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{question}\n\nСТАТЬЯ FAQ:\n{faq_question}\n{faq_answer}"
        async with httpx.AsyncClient(timeout=60) as client:
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
                    "options": {"temperature": 0, "num_predict": 12},
                },
            )
            response.raise_for_status()
            answer = response.json()["message"]["content"].strip().upper()
            for route in ("MATCH", "SUPPORT", "OFFTOPIC"):
                if route in answer:
                    return route
            return "SUPPORT"

    async def available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                return (await client.get(f"{self.base_url}/api/tags")).is_success
        except httpx.HTTPError:
            return False

    async def installed_models(self) -> set[str]:
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                names = {item["name"] for item in response.json().get("models", [])}
                return names | {name.removesuffix(":latest") for name in names}
        except httpx.HTTPError:
            return set()
