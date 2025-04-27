.PHONY: help setup build start stop logs test test-unit test-integration clean format lint migrate

# Default target
help:
	@echo "Webhook Delivery Service"
	@echo ""
	@echo "Usage:"
	@echo "  make setup         - Create necessary directories and files"
	@echo "  make build         - Build Docker images"
	@echo "  make start         - Start all services (API, worker, beat, etc.)"
	@echo "  make stop          - Stop all services"
	@echo "  make logs          - View logs from all services"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make clean         - Remove temporary files and containers"
	@echo "  make format        - Format code with black and isort"
	@echo "  make lint          - Check code style with flake8"
	@echo "  make migrate       - Run database migrations"

# Setup project
setup:
	@echo "Setting up project..."
	@mkdir -p logs
	@mkdir -p .pytest_cache
	@echo "Setup complete"

# Build Docker images
build:
	@echo "Building Docker images..."
	docker-compose build

# Start all services
start:
	@echo "Starting services..."
	docker-compose up -d

# Stop all services
stop:
	@echo "Stopping services..."
	docker-compose down

# View logs
logs:
	@echo "Viewing logs..."
	docker-compose logs -f

# Run all tests
test:
	@echo "Running all tests..."
	pytest -v

# Run unit tests only
test-unit:
	@echo "Running unit tests..."
	pytest -v tests/unit/

# Run integration tests only
test-integration:
	@echo "Running integration tests..."
	pytest -v tests/integration/

# Clean temporary files and containers
clean:
	@echo "Cleaning up..."
	docker-compose down -v
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Format code
format:
	@echo "Formatting code..."
	black app tests
	isort app tests

# Check code style
lint:
	@echo "Checking code style..."
	flake8 app tests

# Run database migrations
migrate:
	@echo "Running database migrations..."
	docker-compose exec api alembic upgrade head 