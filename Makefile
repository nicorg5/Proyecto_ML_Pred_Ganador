# Root Makefile - Delegates to backend Makefile
# This is a convenience wrapper for running commands from the project root

.PHONY: help docker-up docker-down docker-logs api-run test lint format

help:
	@cd backend && make help

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

api-run:
	@cd backend && make api-run

test:
	@cd backend && make test

test-unit:
	@cd backend && make test-unit

test-integration:
	@cd backend && make test-integration

lint:
	@cd backend && make lint

format:
	@cd backend && make format

install-dev:
	@cd backend && make install-dev

ml-pipeline:
	@cd backend && make ml-pipeline

# For any other make target, delegate to backend
%:
	@cd backend && make $@
