PYTHON ?= python3
VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: install generate analyze test coverage lint quality format verify api compose-up compose-down

install:
	$(PYTHON) -m venv --system-site-packages $(VENV)
	$(PIP) install -e ".[dev]"

generate:
	PYTHONPATH=src $(PY) scripts/generate_demo_data.py

analyze:
	MPLCONFIGDIR=tmp/matplotlib PYTHONPATH=src $(PY) scripts/run_demo.py

test:
	PYTHONPATH=src $(PY) -m pytest

coverage:
	PYTHONPATH=src $(PY) -m pytest --cov=process_optimizer --cov-report=term-missing --cov-report=xml

lint:
	$(VENV)/bin/ruff check .
	$(VENV)/bin/ruff format --check .

quality: lint

format:
	$(VENV)/bin/ruff format .
	$(VENV)/bin/ruff check --fix .

verify:
	PYTHONPATH=src $(PY) scripts/verify_repository.py

api:
	PYTHONPATH=src $(PY) -m process_optimizer.cli serve

compose-up:
	docker compose up --build

compose-down:
	docker compose down
