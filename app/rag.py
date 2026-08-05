import asyncio
import json
import time
from dataclasses import dataclass

import chromadb
from chromadb.errors import NotFoundError

from app.config import settings
from app.logger import logger
from app.ollama import OllamaClient


@dataclass
class Hit:
    question: str
    answer: str
    url: str
    relevance: float


class KnowledgeBase:
    def __init__(self, ollama: OllamaClient) -> None:
        settings.safe_chroma_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(settings.safe_chroma_path))
        self._collection()
        self.ollama = ollama
        self._rebuild_lock = asyncio.Lock()

    def _collection(self):
        return self.client.get_or_create_collection(
            "lime_faq", metadata={"hnsw:space": "cosine"}
        )

    @property
    def count(self) -> int:
        return self._collection().count()

    async def rebuild(self) -> int:
        async with self._rebuild_lock:
            logger.info(f"[Chroma] Rebuilding KnowledgeBase index from {settings.safe_knowledge_path}...")
            items = json.loads(settings.safe_knowledge_path.read_text(encoding="utf-8"))
            if not isinstance(items, list) or not items:
                raise ValueError("Knowledge base must be a non-empty JSON array")
            docs = [f"Вопрос: {x['question']}\nОтвет: {x['answer']}" for x in items]
            embeddings = await self.ollama.embed(docs)
            try:
                self.client.delete_collection("lime_faq")
            except (ValueError, NotFoundError):
                pass
            collection = self.client.create_collection(
                "lime_faq", metadata={"hnsw:space": "cosine"}
            )
            collection.add(
                ids=[str(x.get("id", i)) for i, x in enumerate(items)],
                documents=docs,
                embeddings=embeddings,
                metadatas=[{
                    "question": x["question"], "answer": x["answer"],
                    "url": x.get("url", "https://limehd.tv/faq/0")
                } for x in items],
            )
            logger.info(f"[Chroma] Successfully indexed {len(items)} document(s) in vector DB.")
            return len(items)

    async def search(self, query: str, limit: int | None = None) -> list[Hit]:
        t0 = time.perf_counter()
        logger.info(f"[Chroma] Searching KnowledgeBase for query: '{query[:60]}...'")
        if self.count == 0:
            logger.info("[Chroma] KnowledgeBase collection is empty, triggering auto-rebuild...")
            await self.rebuild()
        embedding = (await self.ollama.embed([query]))[0]
        result = self._collection().query(
            query_embeddings=[embedding], n_results=min(limit or settings.top_k, self.count)
        )
        hits: list[Hit] = []
        for meta, distance in zip(result["metadatas"][0], result["distances"][0]):
            relevance = max(0.0, 1.0 - float(distance))
            hits.append(Hit(meta["question"], meta["answer"], meta["url"], relevance))
        top_rel = round(hits[0].relevance, 3) if hits else 0.0
        logger.info(f"[Chroma] Search finished in {round((time.perf_counter() - t0) * 1000)}ms -> found {len(hits)} hit(s), top relevance: {top_rel}")
        return hits
