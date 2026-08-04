import asyncio
import math
from dataclasses import dataclass

from app.ollama import OllamaClient


@dataclass(frozen=True)
class DownloadIntent:
    platform: str | None
    confidence: float


class SemanticIntentRouter:
    """Small embedding-based router for typo-tolerant special actions."""

    INTENT_REFERENCES = (
        "пользователь хочет скачать или установить приложение Lime HD TV на устройство",
        "пользователю нужна версия приложения Lime HD TV для конкретного устройства или платформы",
        "пользователь сообщает о проблеме или ошибке в работе приложения",
    )
    POSITIVE_INTENT_COUNT = 2
    PLATFORM_REFERENCES = {
        "ios": "скачать приложение для iPhone iPad iOS через App Store",
        "android": "скачать приложение для телефона Android через Google Play",
        "android_tv": "скачать приложение для Android TV или приставки",
        "windows": "скачать приложение для компьютера Windows",
        "smart_tv": "установить приложение на Smart TV телевизор LG Samsung",
        "huawei": "скачать приложение для телефона Huawei через AppGallery",
    }

    def __init__(self, ollama: OllamaClient) -> None:
        self.ollama = ollama
        self._reference_embeddings: list[list[float]] | None = None
        self._lock = asyncio.Lock()

    @staticmethod
    def _cosine(left: list[float], right: list[float]) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        denominator = math.sqrt(sum(x * x for x in left)) * math.sqrt(sum(x * x for x in right))
        return numerator / denominator if denominator else 0.0

    async def _references(self) -> list[list[float]]:
        if self._reference_embeddings is None:
            async with self._lock:
                if self._reference_embeddings is None:
                    texts = [*self.INTENT_REFERENCES, *self.PLATFORM_REFERENCES.values()]
                    self._reference_embeddings = await self.ollama.embed(texts)
        return self._reference_embeddings

    async def download_intent(self, message: str) -> DownloadIntent | None:
        query = (await self.ollama.embed([message]))[0]
        references = await self._references()
        intent_count = len(self.INTENT_REFERENCES)
        intent_scores = [self._cosine(query, item) for item in references[:intent_count]]
        download_score = max(intent_scores[:self.POSITIVE_INTENT_COUNT])
        negative_score = max(intent_scores[self.POSITIVE_INTENT_COUNT:])
        if download_score < 0.34 or download_score <= negative_score:
            return None

        platform_names = list(self.PLATFORM_REFERENCES)
        platform_scores = [self._cosine(query, item) for item in references[intent_count:]]
        ranked = sorted(enumerate(platform_scores), key=lambda item: item[1], reverse=True)
        platform: str | None = None
        if ranked and (len(ranked) == 1 or ranked[0][1] >= ranked[1][1] + 0.01):
            platform = platform_names[ranked[0][0]]
        return DownloadIntent(platform=platform, confidence=download_score)
