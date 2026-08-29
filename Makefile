.PHONY: dev gateway test seed db

dev:            ## run the API server with reload
	uv run uvicorn cortex.api.app:create_app --factory --reload --port 8000

gateway:        ## start the LiteLLM proxy
	docker compose up litellm

test:
	uv run pytest -q

seed:           ## capture your first ideas interactively
	uv run python scripts/seed.py

db:             ## open a sqlite shell on the ledger
	sqlite3 data/cortex.db
