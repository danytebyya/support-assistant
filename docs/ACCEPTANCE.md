# Чек-лист приёмки

| Требование | Реализация / проверка |
|---|---|
| Локальная LLM через REST | Ollama `/api/chat`, Qwen 3 8B |
| Embeddings и vector DB | Ollama `qwen3-embedding:0.6b` + persistent ChromaDB cosine |
| Ответ только по контексту | top-k, relevance threshold, закрытый system prompt |
| `POST /chat`, JSON, HTTP-коды | OpenAPI; обработчики 422/429/502/503/504 |
| Вне темы / identity / секреты | Детерминированные guardrails до LLM |
| Rate limit / длина | 20/мин/IP, Pydantic max 1000 |
| 10 пользователей | `scripts/load_test.py --users 10` |
| Логирование | UTF-8 JSONL с UTC и latency |
| Подключаемый виджет | 2 script-тега, Shadow DOM, responsive layout |
| История сессии / новый чат | session UUID и UI reset |
| Источник ответа | `sources[]` + ссылки в виджете |
| Обновление без кода | JSON + `make update-faq reindex` |
| Docker Compose | API, Ollama, model initializer, persistent volumes |
| 20+ тестовых вопросов | `data/evaluation/questions.json` (24 сценария) |

Перед демонстрацией выполнить `docker compose up`, `make reindex`, открыть демо,
проверить `/health`, затем запустить evaluation и load test. Сохранить фактические
JSON-результаты вместе с параметрами машины.
