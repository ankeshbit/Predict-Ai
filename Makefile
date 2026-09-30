.PHONY: help install lint test migrate seed dev-backend dev-frontend clean

help:
	@echo "Predict-Ai (PrediCore) Maintenance Commands:"
	@echo "  make install       Install frontend, backend, and pdm_core dependencies"
	@echo "  make lint          Run linters across ml/, backend/, and frontend/"
	@echo "  make test          Run unit/integration tests for ml/, backend/, and frontend/"
	@echo "  make migrate       Run Alembic migrations against DATABASE_URL_DIRECT"
	@echo "  make seed          Seed initial demo machines and model artifacts"
	@echo "  make dev-backend   Start the FastAPI development server"
	@echo "  make dev-frontend  Start Vite development server"

install:
	python -m pip install -e ml/
	python -m pip install -e backend/
	cd frontend && npm install

lint:
	python -m ruff check ml/ backend/ scripts/
	cd frontend && npm run lint

test:
	python -m pytest ml/tests/ backend/tests/ -v
	cd frontend && npm run build

migrate:
	cd backend && alembic upgrade head

seed:
	cd backend && python -m app.cli seed-demo

dev-backend:
	cd backend && uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
