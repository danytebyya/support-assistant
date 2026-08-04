.PHONY: up down test reindex update-faq logs
up:
	./scripts/start.sh
down:
	docker compose down
test:
	pytest -q
reindex:
	docker compose exec api python scripts/reindex.py
update-faq:
	docker compose exec -T api python scripts/update_faq.py
	docker compose exec -T api python scripts/reindex.py
logs:
	docker compose logs -f api ollama
