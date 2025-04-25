# Webhook Delivery Service
(checklist.md)[checklist.md]

A robust webhook delivery system that ingests, queues, delivers, and tracks webhook deliveries with automatic retries and comprehensive logging.

## Features

- **Subscription Management**: Full CRUD API for webhook subscriptions
- **Webhook Ingestion**: Accepts JSON payloads with optional signature verification
- **Event Type Filtering**: Delivers webhooks only to subscriptions interested in specific event types
- **Asynchronous Processing**: Queues and processes webhook deliveries in the background
- **Automatic Retries**: Implements exponential backoff retry strategy for failed deliveries
- **Comprehensive Logging**: Tracks all delivery attempts with detailed status information
- **Log Retention**: Automatically purges logs older than 72 hours
- **Status & Analytics**: API endpoints for webhook delivery status and subscription history
- **Caching**: Redis-based caching for performance optimization
- **Containerized**: Complete Docker setup for local development and production

## Architecture

This service is built with the following technologies:

- **FastAPI**: Modern, high-performance web framework for building APIs
- **PostgreSQL**: Persistent storage for subscriptions and delivery logs
- **Redis**: Caching and message broker for Celery
- **Celery**: Background task processing for webhook delivery and scheduled cleanup
- **SQLAlchemy**: Database ORM for PostgreSQL
- **Pydantic**: Data validation and settings management
- **Docker & Docker Compose**: Containerization and orchestration
- **Alembic**: Database migrations

### System Components

```
┌─────────────┐       ┌─────────────┐      ┌─────────────┐
│             │       │             │      │             │
│  FastAPI    │──────▶│    Redis    │◀────▶│   Celery    │
│   Server    │       │  (Cache &   │      │  Workers    │
│             │       │   Broker)   │      │             │
└──────┬──────┘       └─────────────┘      └──────┬──────┘
       │                                          │
       │                                          │
       ▼                                          ▼
┌─────────────┐                          ┌─────────────┐
│             │                          │             │
│ PostgreSQL  │                          │  External   │
│  Database   │                          │ Webhook     │
│             │                          │ Targets     │
└─────────────┘                          └─────────────┘
```

## Getting Started

### Prerequisites

- Docker and Docker Compose

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/webhook-delivery-service.git
   cd webhook-delivery-service
   ```

2. Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Run database migrations:
   ```bash
   docker-compose exec app alembic upgrade head
   ```

5. Access the API documentation:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Environment Variables

See `.env.example` for all available configuration options.

## API Documentation

### Subscription Management

**Create Subscription**
```bash
curl -X POST "http://localhost:8000/subscriptions" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com/webhook-receiver",
    "secret_key": "optional-secret",
    "event_types": ["order.created", "order.updated"]
  }'
```

**Get Subscription**
```bash
curl -X GET "http://localhost:8000/subscriptions/{subscription_id}"
```

**Update Subscription**
```bash
curl -X PUT "http://localhost:8000/subscriptions/{subscription_id}" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com/new-endpoint",
    "secret_key": "new-secret",
    "event_types": ["order.created", "order.canceled"]
  }'
```

**Delete Subscription**
```bash
curl -X DELETE "http://localhost:8000/subscriptions/{subscription_id}"
```

### Webhook Ingestion

**Send Webhook (without signature)**
```bash
curl -X POST "http://localhost:8000/ingest/{subscription_id}?event_type=order.created" \
  -H "Content-Type: application/json" \
  -d '{
    "order_id": "12345",
    "status": "confirmed",
    "total": 99.99
  }'
```

**Send Webhook (with signature)**
```bash
# Assuming secret_key is "mysecret" and payload is '{"order_id":"12345"}'
# Signature would be calculated as HMAC-SHA256(payload, secret_key)

curl -X POST "http://localhost:8000/ingest/{subscription_id}?event_type=order.created" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<calculated-signature>" \
  -d '{
    "order_id": "12345",
    "status": "confirmed",
    "total": 99.99
  }'
```

### Status & Analytics

**Get Webhook Delivery Status**
```bash
curl -X GET "http://localhost:8000/status/{delivery_id}"
```

**Get Recent Delivery Attempts for Subscription**
```bash
curl -X GET "http://localhost:8000/subscriptions/{subscription_id}/attempts?limit=20"
```

## Cost Estimation

Based on the requirement of handling 5,000 webhooks per day with an average of 1.2 delivery attempts per webhook:

- **Total webhook deliveries per day**: 5,000 × 1.2 = 6,000
- **Total webhook deliveries per month**: 6,000 × 30 = 180,000

Estimated monthly costs on free-tier cloud services (e.g., Render):

| Service | Free Tier Limits | Monthly Usage | Additional Cost |
|---------|-----------------|---------------|----------------|
| Web Service | 750 hours/month | 720 hours | $0 |
| PostgreSQL | 1GB storage, limited connections | ~200MB for 3 days of logs | $0 |
| Redis | Usually not included in free tier | Minimal usage | ~$5-15 |
| Worker | May require additional instance | 720 hours | ~$7-20 |
| **Total** | | | **$12-35/month** |

Note: This estimation assumes minimal resource requirements and may vary based on actual usage patterns and the specific provider chosen.

## Development

### Project Structure

The codebase follows a modular structure:

- `app/`: Main application package
  - `api/`: API routes and endpoints
  - `models/`: Database models
  - `schemas/`: Pydantic schemas for request/response validation
  - `db/`: Database connection and repositories
  - `cache/`: Redis cache utilities
  - `services/`: Business logic layer
  - `workers/`: Celery tasks and configurations
  - `utils/`: Helper utilities

### Running Tests

```bash
docker-compose exec app pytest
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Credits

- FastAPI: https://fastapi.tiangolo.com/
- Celery: https://docs.celeryproject.org/
- SQLAlchemy: https://www.sqlalchemy.org/
- Redis: https://redis.io/
- PostgreSQL: https://www.postgresql.org/


## Expected Project structure
```bash
webhook-delivery-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── subscriptions.py
│   │   │   ├── webhooks.py
│   │   │   └── status.py
│   │   └── deps.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── subscription.py
│   │   └── delivery_log.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── subscription.py
│   │   ├── webhook.py
│   │   └── delivery.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   └── repositories/
│   │       ├── __init__.py
│   │       ├── subscription_repository.py
│   │       └── delivery_log_repository.py
│   ├── cache/
│   │   ├── __init__.py
│   │   └── redis_cache.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── subscription_service.py
│   │   ├── webhook_service.py
│   │   └── delivery_service.py
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── celery_app.py
│   │   ├── delivery_worker.py
│   │   └── cleanup_worker.py
│   └── utils/
│       ├── __init__.py
│       ├── signature.py
│       └── validators.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_subscription_service.py
│   │   └── test_signature_utils.py
│   └── integration/
│       ├── __init__.py
│       └── test_webhook_flow.py
├── alembic/
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
├── docker/
│   ├── Dockerfile
│   └── entrypoint.sh
├── docker-compose.yml
├── alembic.ini
├── pyproject.toml
├── requirements.txt
├── .env.example
├── README.md
└── checklist.md
```