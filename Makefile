COMPOSE ?= docker compose
SERVICE ?= app
PORT ?= 8501

.PHONY: help build up up-build down restart logs ps shell test local-install local-run clean

help:
	@echo "КлиматикА frontend commands"
	@echo ""
	@echo "  make build         Build Docker image"
	@echo "  make up            Start app container"
	@echo "  make up-build      Build and start app container"
	@echo "  make down          Stop and remove containers"
	@echo "  make restart       Restart app container"
	@echo "  make logs          Follow app logs"
	@echo "  make ps            Show compose services"
	@echo "  make shell         Open shell in app container"
	@echo "  make test          Run pytest in container"
	@echo "  make local-install Install local Python deps"
	@echo "  make local-run     Run Streamlit locally"
	@echo "  make clean         Remove Python caches"

build:
	$(COMPOSE) build $(SERVICE)

up:
	$(COMPOSE) up -d $(SERVICE)

up-build:
	$(COMPOSE) up -d --build $(SERVICE)

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart $(SERVICE)

logs:
	$(COMPOSE) logs -f $(SERVICE)

ps:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec $(SERVICE) sh

test:
	$(COMPOSE) run --rm $(SERVICE) pytest

local-install:
	poetry install

local-run:
	poetry run streamlit run app/main.py --server.port $(PORT)

clean:
	python -c "import shutil; from pathlib import Path; [shutil.rmtree(p, ignore_errors=True) for p in Path('.').rglob('__pycache__')]; shutil.rmtree('.pytest_cache', ignore_errors=True)"
