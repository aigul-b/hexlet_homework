# Variables
PORT ?= 8000

# Install dependencies
.PHONY: install
install:
	uv sync

# Debug the app
.PHONY: dev 
dev:
	uv run flask --debug --app page_analyzer:app run

# Run the application
.PHONY: start
start:
	uv run gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

# Build package
.PHONY: build
build:
	./build.sh

# Run project with gunicorn
.PHONY: render-start
render-start:
	gunicorn -w 5 -b 0.0.0.0:$(PORT) page_analyzer:app

# Run linter
.PHONY: lint
lint:
	uv run pylint src/

