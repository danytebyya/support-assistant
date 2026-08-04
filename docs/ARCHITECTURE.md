# Архитектура Lime AI Support

## Поток запроса

```text
Сайт → widget.js → FastAPI → guardrails → Ollama embeddings → ChromaDB
                                    ↓                         ↓
                              фиксированный ответ      top-k контекст
                                                              ↓
                                              Ollama Qwen 3 → JSON + sources
                                                              ↓
                                                        JSONL audit log
```

1. Виджет отправляет `message` и стабильный `session_id` в `POST /chat`.
2. Pydantic проверяет тип и длину, rate limiter — частоту по IP.
3. Детерминированные правила раньше LLM обрабатывают identity, запросы о
   реализации и явный prompt injection.
4. `qwen3-embedding:0.6b` локально строит мультиязычный embedding запроса. ChromaDB выполняет
   cosine semantic search по FAQ.
5. Низкая релевантность приводит к безопасному отказу. Иначе top-4 фрагмента и
   вопрос передаются Qwen 3 с запретом использовать внешние знания. При высокой
   уверенности (`>= 0.68`) API возвращает утверждённый FAQ напрямую: без
   генеративных искажений и с минимальной задержкой.
6. API возвращает ответ, до двух источников и latency. Обмен пишется в JSONL.

## Компоненты

- `app/main.py` — HTTP-контракты и оркестрация.
- `app/guardrails.py` — доменная политика и системные ограничения.
- `app/rag.py` — идемпотентная индексация и retrieval.
- `app/ollama.py` — локальные REST-вызовы `/api/embed` и `/api/chat`.
- `widget/widget.js` — подключаемый Shadow DOM web component без зависимостей.
- `scripts/update_faq.py` — fail-safe ETL из FAQ в JSON.
- `scripts/evaluate.py` — воспроизводимый acceptance-прогон.

## Решения и границы

Один worker FastAPI выбран намеренно: ChromaDB работает как embedded-хранилище,
а Ollama само управляет очередью модели. Для горизонтального масштабирования
Chroma следует вынести в серверный режим, rate limit — в Redis, а JSONL — в
SQLite/PostgreSQL или журнал событий.

Генеративная модель не определяет критичные политики сама: identity, secret
probing и явные injection-запросы перехватываются до retrieval. Контекст
обрамляется как недоверенные данные. Название модели нигде не возвращается в API.

## Производительность

Embeddings FAQ вычисляются только при reindex и сохраняются на диске. На запрос
строится один embedding, один ANN-поиск и одна генерация с лимитом 300 токенов.
После прогрева типовой ответ укладывается в целевые 5 секунд на подходящем GPU;
фактическая скорость на CPU зависит от железа. Нагрузочный smoke-тест:

```bash
python scripts/load_test.py --url http://localhost:8000/chat --users 10
```

## Расширение

Новый источник должен быть преобразован в тот же JSON-контракт. Для длинных
статей добавляется этап chunking с `source_type`, `title`, `url` в metadata;
retrieval и API источников менять не требуется.
