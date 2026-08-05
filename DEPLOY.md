# Инструкция по развёртыванию проекта Support

Документ содержит точные команды для развёртывания проекта в изолированном Docker-окружении на порту **8080** без конфликтов с другими проектами на сервере.

---

## 1. Копирование проекта на сервер

Перенесите файлы проекта в директорию `/opt/support` на Ubuntu-сервере.

Пример копирования через `rsync` с локальной машины:
```bash
rsync -avz --exclude='.git' --exclude='.venv' --exclude='__pycache__' ./ root@SERVER_IP:/opt/support/
```

Или скопируйте директорию на сервере:
```bash
sudo mkdir -p /opt/support
sudo chown -R $USER:$USER /opt/support
cd /opt/support
```

---

## 2. Создание файла переменных окружения `.env`

Создайте `.env` на основе шаблона `.env.example`:
```bash
cd /opt/support
cp .env.example .env
```

Отредактируйте секреты и параметры в `.env`:
```bash
nano .env
```
> **Важно:** Обязательно смените `ADMIN_TOKEN` на случайный стойкий токен!

---

## 3. Запуск проекта

Запустите проект с помощью отдельного имени проекта `support`:
```bash
docker compose -p support -f docker-compose.prod.yml up -d --build
```

---

## 4. Просмотр статуса и логов

Проверить статус всех контейнеров:
```bash
docker compose -p support -f docker-compose.prod.yml ps
```

Просмотреть логи всех сервисов в реальном времени:
```bash
docker compose -p support -f docker-compose.prod.yml logs -f
```

Просмотреть логи только backend или frontend:
```bash
docker compose -p support -f docker-compose.prod.yml logs -f api
docker compose -p support -f docker-compose.prod.yml logs -f frontend
```

Проверить доступность:
```bash
curl -I http://localhost:8080/health
```

---

## 5. Обновление проекта

Для обновления проекта до новой версии:
```bash
cd /opt/support
# (Скопируйте новые файлы или подтяните git)
docker compose -p support -f docker-compose.prod.yml up -d --build
```

---

## 6. Полная остановка и удаление проекта

Остановка и удаление контейнеров и внутренних сетей (без удаления сохраняемых данных):
```bash
docker compose -p support -f docker-compose.prod.yml down
```

Полное удаление контейнеров, сетей и сохранённых томов (данные ChromaDB и Ollama):
```bash
docker compose -p support -f docker-compose.prod.yml down -v
```

---

## Важные примечания
- **Внешний порт:** Доступен только `http://SERVER_IP:8080`.
- **Изоляция:** Порты backend (8000) и Ollama (11434) не публикуются наружу.
- **База данных:** SQL-миграции не требуются. Векторный индекс ChromaDB инициализируется автоматически из `data/knowledge/faq.json`.
