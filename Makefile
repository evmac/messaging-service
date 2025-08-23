.PHONY: setup run test-unit test clean help db-up db-down db-logs db-shell dev-setup lint format type-check db-reset venv venv-activate venv-deactivate

help:
	@echo "Available commands:"
	@echo "  help        - Show this help message"
	@echo "  setup       - Set up the project environment and start database"
	@echo "  app-setup   - Set up the application"
	@echo "  venv-setup  - Create Python virtual environment"
	@echo "  venv-check  - Check if Python virtual environment exists"
	@echo "  run         - Run the application"
	@echo "  test-unit   - Run Python unit tests"
	@echo "  test        - Run API integration tests with curl"
	@echo "  update-dependencies - Update dependencies to the latest version"
	@echo "  pin-dependencies - Pin dependencies to requirements.txt"
	@echo "  type-check  - Run mypy type checking"
	@echo "  lint        - Run linting tools (flake8, bandit)"
	@echo "  format      - Format code with black and isort"	
	@echo "  precommit   - Run all pre-commit checks"
	@echo "  clean       - Clean up temporary files and stop containers"
	@echo "  db-setup    - Set up the database"
	@echo "  db-up       - Start the PostgreSQL database"
	@echo "  db-down     - Stop the PostgreSQL database"
	@echo "  db-reset    - Reset database (stop, remove volumes, restart)"
	@echo "  db-logs     - Show database logs"
	@echo "  db-shell    - Connect to the database shell"

# Virtual environment management
VENV_DIR := venv
VENV_ACTIVATE := $(VENV_DIR)/bin/activate
PYTHON := python3
PIP := $(VENV_DIR)/bin/pip
PIP_TOOLS := $(VENV_DIR)/bin/pip-compile
UVICORN := $(VENV_DIR)/bin/uvicorn
PYTEST := $(VENV_DIR)/bin/pytest
MYPY := $(VENV_DIR)/bin/mypy
FLAKE8 := $(VENV_DIR)/bin/flake8
BANDIT := $(VENV_DIR)/bin/bandit
BLACK := $(VENV_DIR)/bin/black
ISORT := $(VENV_DIR)/bin/isort

venv-setup:
	@echo "Creating Python virtual environment..."
	@if [ ! -d "$(VENV_DIR)" ]; then \
		$(PYTHON) -m venv $(VENV_DIR); \
		echo "Virtual environment created at $(VENV_DIR)"; \
	else \
		echo "Virtual environment already exists at $(VENV_DIR)"; \
	fi

venv-check:
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Virtual environment not found. Please run 'make venv-setup' first."; \
		exit 1; \
	fi

app-setup: venv-check
	@echo "Installing Python dependencies..."
	@$(PIP) install -r requirements.txt
	@$(PIP) install -r requirements-dev.txt

db-setup:
	@echo "Setting up the database..."
	@docker-compose up -d
	@echo "Waiting for database to be ready..."
	@sleep 5
	@echo "Database setup complete!"

setup: venv-setup app-setup db-setup

run:
	@echo "Running the application..."
	@./bin/start.sh

test-unit: venv-check
	@echo "Running unit tests..."
	@$(PYTEST) tests/ -v

test:
	@echo "Running tests..."
	@echo "Starting test database if not running..."
	@docker-compose up -d
	@echo "Running test script..."
	@./bin/test.sh

update-dependencies: venv-check
	@echo "Updating dependencies..."
	@$(PIP_TOOLS) --upgrade requirements.in
	@$(PIP_TOOLS) --upgrade requirements-dev.in

pin-dependencies: venv-check
	@echo "Pinning dependencies..."
	@$(PIP) freeze > requirements.txt

type-check: venv-check
	@echo "Running type checking..."
	@$(MYPY) app/ lib/

lint: venv-check
	@echo "Running linting tools..."
	@$(FLAKE8) --max-line-length 88 app/ tests/ lib/
	@$(BANDIT) -r app/ lib/

format: venv-check
	@echo "Formatting code..."
	@$(BLACK) app/ tests/ lib/
	@$(ISORT) app/ tests/ lib/

precommit: pin-dependencies format type-check lint test-unit

clean:
	@echo "Cleaning up..."
	@echo "Stopping and removing containers..."
	@docker-compose down -v
	@echo "Removing virtual environment..."
	@rm -rf $(VENV_DIR)
	@echo "Removing any temporary files..."
	@rm -rf *.log *.tmp __pycache__ .pytest_cache .mypy_cache
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true

db-up:
	@echo "Starting PostgreSQL database..."
	@docker-compose up -d

db-down:
	@echo "Stopping PostgreSQL database..."
	@docker-compose down

db-reset: db-down db-up
	@sleep 10

db-logs:
	@echo "Showing database logs..."
	@docker-compose logs -f postgres

db-shell:
	@echo "Connecting to database shell..."
	@docker-compose exec postgres psql -U messaging_user -d messaging_service
