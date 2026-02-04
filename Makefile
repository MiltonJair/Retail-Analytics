.PHONY: help setup test api dashboard docker-build docker-run clean

help:
	@echo "Available commands:"
	@echo "  make setup        - Install dependencies"
	@echo "  make test         - Run unit tests"
	@echo "  make api          - Start API server"
	@echo "  make dashboard    - Start Streamlit dashboard"
	@echo "  make db           - Initialize database"
	@echo "  make docker-build - Build Docker image"
	@echo "  make docker-run   - Run with docker-compose"
	@echo "  make clean        - Remove __pycache__ and .pytest_cache"

setup:
	python -m venv .venv
	.venv\Scripts\pip install --upgrade pip
	.venv\Scripts\pip install -r requirements.txt

test:
	.venv\Scripts\python -m pytest tests/ -v --tb=short

api:
	.venv\Scripts\python -m uvicorn src.api.main:app --reload

dashboard:
	.venv\Scripts\python -m streamlit run src/analytics/dashboard.py

db:
	.venv\Scripts\python setup.py

docker-build:
	docker build -t walmart-analytics .

docker-run:
	docker-compose up --build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
