.PHONY: up down logs ps clean help

## Start the thesis prototype
up:
	docker compose up --build

## Stop
down:
	docker compose down

## Logs
logs:
	docker compose logs -f

## Status
ps:
	docker compose ps

## Remove containers and stored documents
clean:
	docker compose down -v --remove-orphans

help:
	@echo "GED Management AI"
	@echo "  make up     start"
	@echo "  make down   stop"
	@echo "  make logs   follow logs"
	@echo "  make clean  stop and delete stored documents"
