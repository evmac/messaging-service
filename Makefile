.ONESHELL:

.PHONY: help venv-setup venv-check venv-activate venv-deactivate venv venv-deactivate venv-activate venv-check venv-setup setup run test-unit test update type-check lint format precommit clean db-setup db-up db-down db-logs db-shell providers-setup providers-up providers-down providers-logs providers-reset

help:
	@echo "Available commands:"
	@echo "  help        - Show this help message"
	@echo "  setup       - Set up the project environment and start database and provider services"
	@echo "  venv        - Create and activate Python virtual environment"
	@echo "  run         - Run the application"
	@echo "  test-unit   - Run Python unit tests"
	@echo "  test        - Run API integration tests with curl"
	@echo "  update      - Update dependencies to the latest version"
	@echo "  type-check  - Run mypy type checking"
	@echo "  lint        - Run linting tools (flake8, bandit)"
	@echo "  format      - Format code with black, isort, and autoflake"
	@echo "  autofix     - Auto-fix lint issues and run all checks"
	@echo "  precommit   - Run all pre-commit checks"
	@echo "  clean       - Clean up temporary files and stop containers"
	@echo "  db-reset    - Reset database (stop, remove volumes, restart)"
	@echo "  db-logs     - Show database logs"
	@echo "  db-shell    - Connect to the database shell"
	@echo "  providers-reset - Reset the provider services (stop, restart)"
	@echo "  providers-logs  - Show provider service logs"

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
AUTOFLAKE := $(VENV_DIR)/bin/autoflake

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
		echo "Virtual environment not found. Please run 'make setup' first."; \
		exit 1; \
	fi

app-setup: venv-check
	@echo "Installing Python dependencies..."
	@$(PIP) install -r requirements.txt
	@$(PIP) install -r requirements-dev.txt

setup: venv-setup db-setup providers-setup app-setup

run: venv-check
	@echo "Running the application..."
	@./bin/start.sh

test-unit: venv-check
	@echo "Running unit tests..."
	@$(PYTEST) tests/ -v

test:
	@echo "Running tests..."
	@echo "Starting test dependencies if not running..."
	@docker-compose up -d
	@echo "Running test script..."
	@./bin/test.sh

test-integration:
	@echo "Running integration tests..."
	@echo "Starting test dependencies if not running..."
	@docker-compose up -d
	@echo "Running message sending integration tests..."
	@./bin/test_message_sending_integration.sh

update: venv-check
	@echo "Updating dependencies..."
	@$(PIP_TOOLS) --upgrade requirements.in
	@$(PIP_TOOLS) --upgrade requirements-dev.in

type-check: venv-check
	@echo "Running type checking..."
	@$(MYPY) app/ lib/ providers/ tests/

lint: venv-check
	@echo "Running linting tools..."
	@$(FLAKE8) --max-line-length 88 app/ lib/ providers/ tests/
	@$(BANDIT) -r app/ lib/ providers/

format: venv-check
	@echo "Formatting code..."
	@echo "Removing unused imports..."
	@$(AUTOFLAKE) --remove-all-unused-imports --recursive --in-place app/ lib/ providers/ tests/
	@echo "Formatting with black..."
	@$(BLACK) app/ lib/ providers/ tests/
	@echo "Sorting imports with isort..."
	@$(ISORT) app/ lib/ providers/ tests/

precommit: format type-check lint test-unit

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

db-setup:
	@echo "Setting up the database..."
	@docker-compose up -d postgres
	@echo "Waiting for database to be ready..."
	@sleep 3
	@echo "Database setup complete!"

db-up:
	@echo "Starting PostgreSQL database..."
	@docker-compose up -d postgres

db-down:
	@echo "Stopping PostgreSQL database..."
	@docker-compose down postgres

db-reset: db-down db-up
	@sleep 5

db-logs:
	@echo "Showing database logs..."
	@docker-compose logs -f postgres

db-shell:
	@echo "Connecting to database shell..."
	@docker-compose exec postgres psql -U messaging_user -d messaging_service

providers-setup:
	@echo "Setting up provider services..."
	@docker-compose up -d sms-provider email-provider
	@echo "Waiting for provider services to be ready..."
	@sleep 2
	@echo "Provider services setup complete!"

providers-up:
	@echo "Starting provider services..."
	@docker-compose up -d sms-provider email-provider

providers-down:
	@echo "Stopping provider services..."
	@docker-compose down sms-provider email-provider

providers-reset: providers-down providers-up

providers-logs:
	@echo "Showing provider service logs..."
	@docker-compose logs -f sms-provider email-provider
