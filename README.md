# Lime AI Support

Полностью локальный RAG-ассистент поддержки Lime HD TV: FastAPI, Ollama,
ChromaDB и независимый JavaScript-виджет без UI-фреймворков. Внешние AI API не
используются; вопросы, embeddings, найденный контекст и генерация остаются на
вашей машине.

При запуске выбирается подходящий вариант Ollama: нативная универсальная сборка
с Metal для macOS либо актуальный multi-arch Docker-образ для Linux/Windows.
Docker автоматически выбирает `amd64` или `arm64`. Основные Python-зависимости
закреплены точными версиями; тестовые пакеты не попадают в production-образ.

## Быстрый запуск

Требования: Docker Desktop / Docker Engine с Compose, 12+ ГБ свободной RAM и
около 8 ГБ диска. Первый запуск скачивает Ollama и обе модели, поэтому занимает
больше времени; последующие запуски используют локальный кэш.

macOS и Linux:

```bash
cp .env.example .env
./scripts/start.sh
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
.\scripts\start.ps1
```

Скрипты сами скачивают модели `qwen3:8b` и `qwen3-embedding:0.6b`, запускают
API и создают индекс базы знаний. На macOS Ollama сохраняется в `.runtime`, если
она не была установлена ранее. Для фиксации конкретного Docker-образа задайте
`OLLAMA_IMAGE`, например `ollama/ollama:0.32.5`.

Откройте:

- демо виджета — <http://localhost:8000/>
- OpenAPI — <http://localhost:8000/docs>
- состояние — <http://localhost:8000/health>

В режиме Docker папка `widget/` подключена к контейнеру напрямую, а кэш для
демо отключён. Поэтому изменения в `widget.js` и `demo.html` появляются после
обычного обновления страницы без повторной сборки образа.

Для менее мощной машины замените `OLLAMA_CHAT_MODEL` в `.env` на локально
доступную модель меньшего размера и измените модель в `model-init`.

## Подключение виджета

```html
<script src="http://localhost:8000/widget/widget.js"></script>
<script>
  LimeAI.init({
    apiUrl: "http://localhost:8000",
    title: "Лайм AI",
    onboarding: true,
    icons: {
      chat: "/widget/assets/chat.svg",
      edit: "/widget/assets/edit.svg",
      send: "/widget/assets/send.svg",
      close: "/widget/assets/close.svg",
      logo: "/widget/assets/logo.png"
    }
  });
</script>
```

Виджет изолирует стили через Shadow DOM, адаптируется к мобильному экрану,
показывает источники и доступен с клавиатуры. Одноразовый onboarding затемняет
фон, подсвечивает кнопку и исчезает после первого взаимодействия. Его можно
отключить параметром `onboarding: false`.
Собственные SVG, PNG или WebP можно положить в `widget/assets/`. Любой ключ в
`icons` необязателен: если файл не указан, используется встроенная SVG-иконка.

## Примеры API

```bash
curl -s http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"Почему тормозит видео?"}'
```

```json
{
  "answer": "Проверьте стабильность соединения...",
  "session_id": "8bc...",
  "sources": [{"question": "Почему видео тормозит или зависает?", "url": "https://limehd.tv/faq/0", "relevance": 0.82}],
  "latency_ms": 943
}
```

Потоковый SSE-совместимый endpoint: `POST /chat/stream`. Он отправляет итоговое
событие с тем же контрактом; транспорт уже готов к посимвольному streaming при
переходе на потоковый Ollama API.

## База знаний

`data/knowledge/faq.json` — внешний JSON, поэтому вопросы можно добавлять без
изменения кода. После редактирования выполните `make reindex`.

В репозитории находится 31 статья: все 14 уникальных вопросов, опубликованных
на официальной странице Lime HD TV на 2026-08-04, и 17 непересекающихся статей
по темам ТЗ. Серверный запрос к `limehd.tv/faq/0` возвращает anti-bot challenge,
поэтому официальный набор был проверен через отображаемую страницу в браузере.
Импортёр
`scripts/update_faq.py` поддерживает FAQPage JSON-LD и распространённую
accordion-разметку, атомарно заменяет JSON и никогда не стирает рабочую базу,
если вместо FAQ получена защитная страница.

```bash
make update-faq
make reindex
```

Дополнительные источники подключаются тем же JSON-контрактом: `id`, `question`,
`answer`, `url`, необязательный `category`.

## Проверка

```bash
python -m pip install -r requirements-dev.txt
python -m compileall app scripts
pytest -q
python scripts/evaluate.py --api http://localhost:8000
```

Последняя команда прогоняет 24 вопроса: тематические, оффтоп, идентификацию и
попытки раскрытия внутренних инструкций. Отчёт пишется в
`docs/evaluation-results.json`. Целевой порог по содержательным RAG-вопросам —
не менее 80%. Результаты зависят от модели и оборудования, поэтому в репозитории
нет выдуманного «успешного» результата до фактического запуска.

## Эксплуатация и безопасность

- Ограничение: 1000 символов и 20 запросов в минуту с IP.
- Предсказуемые ответы для identity, off-topic и prompt injection.
- Генерация только по найденному контексту, temperature 0.1.
- JSONL-аудит в `data/logs/chat.jsonl` (UTC, session, вопрос, ответ, latency).
- CORS задаётся `ALLOWED_ORIGINS`; в production не оставляйте `*`.
- Административный reindex защищён заголовком `X-Admin-Token`; обязательно
  замените `ADMIN_TOKEN` из примера окружения.
- `/health` подходит для мониторинга. Ошибки модели возвращаются как 503/504.

Подробности: [архитектура](docs/ARCHITECTURE.md) и
[чек-лист приёмки](docs/ACCEPTANCE.md).
