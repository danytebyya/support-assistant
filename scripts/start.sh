#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHAT_MODEL="${OLLAMA_CHAT_MODEL:-qwen3:8b}"
EMBED_MODEL="${OLLAMA_EMBED_MODEL:-qwen3-embedding:0.6b}"
MAC_DOWNLOAD_URL="${OLLAMA_MAC_DOWNLOAD_URL:-https://ollama.com/download/Ollama-darwin.zip}"
DRY_RUN=false

if [[ "${1:-}" == "--dry-run" ]]; then DRY_RUN=true; fi

say() { printf '%s\n' "$*"; }
run() {
  if $DRY_RUN; then printf '+ '; printf '%q ' "$@"; printf '\n'; else "$@"; fi
}
require() {
  command -v "$1" >/dev/null 2>&1 || { say "Ошибка: требуется $1" >&2; exit 1; }
}
compose() { run docker compose "$@"; }

start_docker_ollama() {
  require docker
  say "Платформа: $(uname -s)/$(uname -m). Ollama будет запущена в Docker."
  say "Docker автоматически скачает актуальный образ для архитектуры устройства."
  export OLLAMA_URL="http://ollama:11434"
  compose --profile docker-ollama up -d ollama
  compose --profile docker-ollama run --rm model-init
  compose up -d --build api
  compose exec -T api python scripts/reindex.py
}

find_mac_ollama() {
  if command -v ollama >/dev/null 2>&1; then command -v ollama; return; fi
  if [[ -x /Applications/Ollama.app/Contents/Resources/ollama ]]; then
    printf '%s\n' /Applications/Ollama.app/Contents/Resources/ollama
    return
  fi
  if [[ -x "$ROOT_DIR/.runtime/Ollama.app/Contents/Resources/ollama" ]]; then
    printf '%s\n' "$ROOT_DIR/.runtime/Ollama.app/Contents/Resources/ollama"
    return
  fi
  return 1
}

install_mac_ollama() {
  require curl
  require unzip
  local runtime="$ROOT_DIR/.runtime" archive="$ROOT_DIR/.runtime/Ollama-darwin.zip"
  say "Ollama не найдена. Скачиваю актуальную универсальную сборку для macOS…" >&2
  run mkdir -p "$runtime" >&2
  run curl -fL --retry 3 "$MAC_DOWNLOAD_URL" -o "$archive" >&2
  run unzip -q -o "$archive" -d "$runtime" >&2
  run rm -f "$archive" >&2
  printf '%s\n' "$runtime/Ollama.app/Contents/Resources/ollama"
}

start_macos() {
  require docker
  say "Платформа: macOS/$(uname -m). Используется нативная Ollama с Metal."
  local ollama_bin
  ollama_bin="$(find_mac_ollama || true)"
  if [[ -z "$ollama_bin" ]]; then ollama_bin="$(install_mac_ollama)"; fi
  if $DRY_RUN; then
    say "+ OLLAMA_HOST=0.0.0.0:11434 $ollama_bin serve"
    say "+ OLLAMA_HOST=http://127.0.0.1:11434 $ollama_bin pull $EMBED_MODEL"
    say "+ OLLAMA_HOST=http://127.0.0.1:11434 $ollama_bin pull $CHAT_MODEL"
  else
    mkdir -p "$ROOT_DIR/data/logs"
    if ! curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
      OLLAMA_HOST=0.0.0.0:11434 nohup "$ollama_bin" serve >"$ROOT_DIR/data/logs/ollama.log" 2>&1 &
      for _ in {1..30}; do
        curl -fsS http://127.0.0.1:11434/api/version >/dev/null 2>&1 && break
        sleep 1
      done
    fi
    curl -fsS http://127.0.0.1:11434/api/version >/dev/null || { say "Ollama не запустилась. См. data/logs/ollama.log" >&2; exit 1; }
    OLLAMA_HOST=http://127.0.0.1:11434 "$ollama_bin" pull "$EMBED_MODEL"
    OLLAMA_HOST=http://127.0.0.1:11434 "$ollama_bin" pull "$CHAT_MODEL"
  fi
  export OLLAMA_URL="http://host.docker.internal:11434"
  compose up -d --build api
  compose exec -T api python scripts/reindex.py
}

cd "$ROOT_DIR"
if [[ ! -f .env ]]; then
  run cp .env.example .env
  say "Создан .env из .env.example"
fi
case "$(uname -s)" in
  Darwin) start_macos ;;
  Linux) start_docker_ollama ;;
  *) say "Эта ОС запускается через Docker. В Windows используйте scripts/start.ps1." >&2; exit 1 ;;
esac

say "Готово: http://localhost:8000"
