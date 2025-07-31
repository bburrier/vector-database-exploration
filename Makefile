# Simple Vector Database Makefile

BACKEND_PORT := 8000
FRONTEND_PORT := 3000
BACKEND_PID := .backend.pid
FRONTEND_PID := .frontend.pid

.PHONY: help start status stop logs

help:
	@echo "Vector Database Exploration:\n"
	@echo "  make start  - Start frontend and backend"
	@echo "  make status - Show status of services"
	@echo "  make stop   - Stop frontend and backend"
	@echo "  make logs   - Show logs\n"

start:
	@cd backend && python3 -m uvicorn app:app --host 0.0.0.0 --port $(BACKEND_PORT) --reload > ../$(BACKEND_PID) 2>&1 & echo $$! > ../$(BACKEND_PID)
	@cd frontend && python3 -m http.server $(FRONTEND_PORT) > ../$(FRONTEND_PID) 2>&1 & echo $$! > ../$(FRONTEND_PID)
	@echo "Servers started"

status:
	@if [ -f $(BACKEND_PID) ] && ps -p $$(cat $(BACKEND_PID)) > /dev/null 2>&1; then \
		echo "✓ Backend running (PID: $$(cat $(BACKEND_PID)))"; \
	else \
		echo "✗ Backend not running"; \
	fi
	@if [ -f $(FRONTEND_PID) ] && ps -p $$(cat $(FRONTEND_PID)) > /dev/null 2>&1; then \
		echo "✓ Frontend running (PID: $$(cat $(FRONTEND_PID)))"; \
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

logs:
	@if [ -f $(BACKEND_PID) ]; then \
		echo "Backend logs:"; \
		tail -10 $(BACKEND_PID); \
	else \
		echo "No backend logs"; \
	fi
	@if [ -f $(FRONTEND_PID) ]; then \
		echo "Frontend logs:"; \
		tail -10 $(FRONTEND_PID); \
	else \
		echo "No frontend logs"; \
	fi 