# ServeML Development Makefile

.PHONY: help setup run-backend run-frontend run test clean

help:
	@echo "ServeML Development Commands:"
	@echo "  make setup       - Set up development environment"
	@echo "  make run-backend - Run backend server"
	@echo "  make run-frontend - Run frontend server"
	@echo "  make run         - Run both backend and frontend"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Clean up generated files"

setup:
	@echo "Setting up development environment..."
	cd backend && python -m venv venv
	cd backend && ./venv/bin/pip install -r requirements.txt
	@echo "Creating test model..."
	cd backend && ./venv/bin/python ../create_test_model.py
	@echo "Setup complete!"

run-backend:
	@echo "Starting backend server..."
	cd backend && ./venv/bin/uvicorn app:app --reload --host 0.0.0.0 --port 8000

run-frontend:
	@echo "Starting frontend server..."
	cd frontend && python -m http.server 3000

run:
	@echo "Starting ServeML..."
	@make -j2 run-backend run-frontend

run-docker:
	@echo "Starting ServeML with Docker..."
	docker-compose up

test:
	@echo "Running tests..."
	cd backend && ./venv/bin/pytest -v

clean:
	@echo "Cleaning up..."
	rm -rf backend/uploads/*
	rm -rf backend/__pycache__
	rm -rf backend/venv
	rm -rf test_models
	@echo "Cleanup complete!"