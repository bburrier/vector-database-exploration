# Simple Vector Database Makefile

BACKEND_PORT := 8000
FRONTEND_PORT := 3000
BACKEND_PID := .backend.pid
FRONTEND_PID := .frontend.pid
VENV := $(shell pwd)/venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

.PHONY: help setup start status stop logs clean kill

help:
	@echo "Vector Database Exploration:\n"
	@echo "  make setup  - Create virtual environment and install dependencies"
	@echo "  make start  - Start frontend and backend"
	@echo "  make status - Show status of services"
	@echo "  make stop   - Stop frontend and backend"
	@echo "  make kill   - Kill any orphaned processes on ports"
	@echo "  make logs   - Show logs"
	@echo "  make test   - Run unit tests\n"

setup:
	@echo "Setting up virtual environment..."
	@if [ ! -d "$(VENV)" ]; then \
		python3 -m venv $(VENV); \
		echo "Virtual environment created"; \
	else \
		echo "Virtual environment already exists"; \
	fi
	@echo "Installing dependencies..."
	@$(PIP) install -r backend/requirements.txt
	@echo "Setup complete! Run 'make start' to start the servers"

start:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@cd backend && $(PYTHON) app.py > ../backend.log 2>&1 &
	@cd frontend && python3 -m http.server $(FRONTEND_PORT) > ../frontend.log 2>&1 &
	@echo "Waiting for servers to start..."
	@sleep 8
	@echo "Checking server status..."
	@./scripts/update_pids.sh
	@echo "Servers started:"
	@echo "  Backend (API + static): http://localhost:$(BACKEND_PORT)"
	@echo "  Frontend (hot reload): http://localhost:$(FRONTEND_PORT)"
	@echo "  Use frontend URL for development with hot reloads"

status:
	@if [ -f $(BACKEND_PID) ] && ps -p $$(cat $(BACKEND_PID)) > /dev/null 2>&1; then \
		echo "✓ Backend running (PID: $$(cat $(BACKEND_PID)))"; \
		echo "  API + static: http://localhost:$(BACKEND_PORT)"; \
	else \
		echo "✗ Backend not running"; \
	fi
	@if [ -f $(FRONTEND_PID) ] && ps -p $$(cat $(FRONTEND_PID)) > /dev/null 2>&1; then \
		echo "✓ Frontend running (PID: $$(cat $(FRONTEND_PID)))"; \
		echo "  Hot reload: http://localhost:$(FRONTEND_PORT)"; \
	else \
		echo "✗ Frontend not running"; \
	fi

stop:
	@if [ -f $(BACKEND_PID) ]; then \
		kill $$(cat $(BACKEND_PID)) 2>/dev/null; \
		rm -f $(BACKEND_PID); \
		echo "Backend stopped"; \
	fi
	@if [ -f $(FRONTEND_PID) ]; then \
		kill $$(cat $(FRONTEND_PID)) 2>/dev/null; \
		rm -f $(FRONTEND_PID); \
		echo "Frontend stopped"; \
	fi

kill:
	@echo "Killing orphaned processes on ports $(BACKEND_PORT) and $(FRONTEND_PORT)..."
	@lsof -ti:$(BACKEND_PORT) 2>/dev/null | xargs kill -9 2>/dev/null || echo "No processes on port $(BACKEND_PORT)"
	@lsof -ti:$(FRONTEND_PORT) 2>/dev/null | xargs kill -9 2>/dev/null || echo "No processes on port $(FRONTEND_PORT)"
	@rm -f $(BACKEND_PID) $(FRONTEND_PID)
	@echo "Kill complete"

logs:
	@if [ -f backend.log ]; then \
		echo "Backend logs:"; \
		tail -10 backend.log; \
	else \
		echo "No backend logs"; \
	fi
	@if [ -f frontend.log ]; then \
		echo "Frontend logs:"; \
		tail -10 frontend.log; \
	else \
		echo "No frontend logs"; \
	fi

clean:
	@echo "Cleaning up..."
	@make stop
	@rm -rf $(VENV)
	@rm -rf htmlcov
	@rm -f .coverage

test:
	@if [ ! -d "$(VENV)" ]; then \
		echo "Virtual environment not found. Run 'make setup' first."; \
		exit 1; \
	fi
	@echo "Installing test dependencies..."
	@$(PIP) install -r requirements-test.txt
	@echo "Running tests..."
	@$(PYTHON) -m pytest tests/ -v --tb=short
	@echo "Tests completed!" 