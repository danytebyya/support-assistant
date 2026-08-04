$ErrorActionPreference = "Stop"

Set-Location (Resolve-Path "$PSScriptRoot\..")
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Создан .env из .env.example"
}
$env:OLLAMA_URL = "http://ollama:11434"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop не найден. Установите и запустите Docker Desktop."
}

Write-Host "Windows: Docker скачает актуальный образ Ollama для архитектуры устройства."
docker compose --profile docker-ollama up -d ollama
if ($LASTEXITCODE -ne 0) { throw "Не удалось запустить Ollama" }

docker compose --profile docker-ollama run --rm model-init
if ($LASTEXITCODE -ne 0) { throw "Не удалось скачать модели" }

docker compose up -d --build api
if ($LASTEXITCODE -ne 0) { throw "Не удалось запустить API" }

docker compose exec -T api python scripts/reindex.py
if ($LASTEXITCODE -ne 0) { throw "Не удалось создать индекс базы знаний" }

Write-Host "Готово: http://localhost:8000"
