# Webhook Delivery Service

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

## Live Application

The application is deployed and available at: [https://webhook-production-a5f2.up.railway.app/](https://webhook-production-a5f2.up.railway.app/)

## Monitoring

- **Health Check**: `GET https://webhook-production-a5f2.up.railway.app/health`
- **System Metrics**: `GET https://webhook-production-a5f2.up.railway.app/monitor`

### Flower Dashboard

- **Local (Docker Compose)**: Visit `http://localhost:5555`

## Sample Usage (curl Commands)

### Manage Subscriptions

```bash
# Create a subscription
curl -X POST https://webhook-production-a5f2.up.railway.app/subscriptions \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com/endpoint",
    "event_types": ["order.created", "user.signed_up"]
  }'

# Get a subscription by ID
curl https://webhook-production-a5f2.up.railway.app/subscriptions/<subscription_id>

# Update a subscription
curl -X PUT https://webhook-production-a5f2.up.railway.app/subscriptions/<subscription_id> \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'

# Delete a subscription
curl -X DELETE https://webhook-production-a5f2.up.railway.app/subscriptions/<subscription_id>
```

### Ingest Webhooks

```bash
curl -X POST https://webhook-production-a5f2.up.railway.app/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "subscription_id": "<subscription_id>",
    "payload": {"order_id":"12345"},
    "event_type": "order.created"
  }'
```

### Check Webhook Delivery Status

```bash
curl https://webhook-production-a5f2.up.railway.app/status/<webhook_id>
```

### Retrieve System Metrics

```bash
curl https://webhook-production-a5f2.up.railway.app/monitor
```

## Architecture Choices

This service is built with the following technologies:

- **FastAPI**: Modern, high-performance web framework for building APIs with automatic OpenAPI documentation
- **PostgreSQL**: Persistent storage for subscriptions and delivery logs, chosen for its reliability and advanced features
- **Redis**: Used for both caching and as a message broker for Celery, providing high performance for both use cases
- **Celery**: Distributed task queue for handling asynchronous webhook delivery and scheduled cleanup tasks
- **SQLAlchemy**: Database ORM for PostgreSQL, providing type safety and query optimization
- **Pydantic**: Data validation and settings management, integrating seamlessly with FastAPI
- **Docker & Docker Compose**: Containerization and orchestration for consistent environments
- **Alembic**: Database migrations for version control of database schema

### Retry Strategy

The service implements an exponential backoff retry strategy with the following characteristics:
- Initial retry after 30 seconds
- Subsequent retries at 2, 4, 8, and 15 minutes
- Maximum of 5 retry attempts before marking delivery as permanently failed
- Each retry is logged with complete response information

### Async Task System

Webhook delivery is handled asynchronously through Celery tasks:
- When a webhook is ingested, it's immediately placed in a Celery queue
- Workers pick up tasks based on priority and process them independently
- Failed deliveries are re-queued with a delay based on the retry strategy
- Periodic tasks handle cleanup of old delivery logs

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

## Database Schema and Indexing

### Subscription Model

```sql
CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    target_url VARCHAR(255) NOT NULL,
    secret_key VARCHAR(255),
    event_types JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_subscriptions_is_active ON subscriptions(is_active);
CREATE INDEX idx_subscriptions_event_types ON subscriptions USING GIN(event_types);
```

### DeliveryLog Model

```sql
CREATE TABLE delivery_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID NOT NULL REFERENCES subscriptions(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL,
    response_status_code INTEGER,
    response_body TEXT,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_delivery_logs_subscription_id ON delivery_logs(subscription_id);
CREATE INDEX idx_delivery_logs_status ON delivery_logs(status);
CREATE INDEX idx_delivery_logs_next_retry_at ON delivery_logs(next_retry_at) WHERE next_retry_at IS NOT NULL;
CREATE INDEX idx_delivery_logs_created_at ON delivery_logs(created_at);
```

### Indexing Strategy

- **UUID Primary Keys**: Used for uniqueness and security (not exposing sequential IDs)
- **Foreign Key Constraints**: Ensure referential integrity
- **GIN Index on event_types**: Optimizes the JSON array lookups for event type filtering
- **Index on next_retry_at**: Speeds up the query to find webhooks due for retry
- **Index on created_at**: Helps with efficient log cleanup based on age
- **Compound Indexes**: On frequently queried combinations like subscription_id + status

## Docker Containerization

This service is fully containerized using Docker and Docker Compose, making it easy to run the entire application stack locally or in production environments.

### Container Architecture

The application is structured into several containerized services:

1. **API Service (`api`)**: 
   - FastAPI application serving the REST API endpoints
   - Handles API requests and queues webhook delivery tasks
   - Uses uvicorn with optional reload mode in development

2. **Celery Worker (`worker`)**:
   - Processes asynchronous webhook delivery tasks
   - Implements retry mechanism for failed deliveries
   - Handles webhook delivery requests to external endpoints

3. **Celery Beat (`beat`)**:
   - Scheduled task scheduler for maintenance jobs
   - Runs periodic cleanup of old webhook delivery logs
   - Manages other recurring tasks

4. **Flower Dashboard (`flower`)**:
   - Web-based monitoring tool for Celery tasks
   - Provides visualization of task queues, success/failure rates
   - Available at http://localhost:5555 when the stack is running

5. **PostgreSQL Database (`db`)**:
   - Persistent storage for subscriptions and delivery logs
   - Pre-configured with appropriate indexes for performance

6. **Redis (`redis`)**:
   - Serves as both cache and message broker
   - Stores Celery task queue and results
   - Provides caching for subscription data

### Production-Ready Features

The Docker setup includes several production-grade features:

- **Multi-Stage Builds**: Optimizes container size and improves security
- **Non-Root User**: Containers run as a non-privileged user for security
- **Health Checks**: All services have configured health checks
- **Graceful Shutdown**: Proper signal handling for clean termination
- **Automatic Restarts**: Services restart on failure
- **Properly Separated Logs**: Each service logs to its own log file
- **Volume Persistence**: Database and Redis data persist across restarts
- **Environment Configuration**: Easily configurable via environment variables

### Running with Docker Compose

1. **Start the complete stack**:
   ```bash
   make start
   # or
   docker-compose up -d
   ```

2. **Check service status**:
   ```bash
   docker-compose ps
   ```

3. **View logs from all services**:
   ```bash
   make logs
   # or
   docker-compose logs -f
   ```

4. **View logs from a specific service**:
   ```bash
   docker-compose logs -f api
   ```

5. **Run database migrations**:
   ```bash
   make migrate
   # or
   docker-compose exec api alembic upgrade head
   ```

6. **Stop all services**:
   ```bash
   make stop
   # or
   docker-compose down
   ```

7. **Complete cleanup (including volumes)**:
   ```bash
   make clean
   # or
   docker-compose down -v
   ```

### Container Role Configuration

Each service container is configured using the `CONTAINER_ROLE` environment variable, which enables us to use the same container image for different roles. The possible values are:

- `api`: Runs the FastAPI application
- `worker`: Runs the Celery worker for processing webhook deliveries
- `beat`: Runs the Celery beat scheduler for periodic tasks
- `flower`: Runs the Flower monitoring dashboard

This approach simplifies container management and ensures consistency across all containers.

### Development with Docker

For local development, the Docker setup provides several features:

- **Auto-reload**: The API container automatically reloads when code changes in development mode
- **Volume mounting**: Local logs are stored in the `./logs` directory for easy access
- **Database persistence**: PostgreSQL data persists in a Docker volume

## Setup Instructions

### Prerequisites

- Docker and Docker Compose

### Local Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/sanskarpan/Webhook.git
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

## API Usage Examples

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

**List All Subscriptions**
```bash
curl -X GET "http://localhost:8000/subscriptions"
```

### Webhook Ingestion

**Send Webhook (Signature Required)**
```bash
# Calculate signature: HMAC-SHA256(canonical_json_payload, secret_key)
# Canonical JSON: JSON.stringify(payload, null, 0) with keys sorted alphabetically
# Example: For payload {"order_id":"12345"} and secret_key "mysecret"

curl -X POST "http://localhost:8000/ingest/{subscription_id}?event_type=order.created" \
  -H "Content-Type: application/json" \
  -H "X-Hub-Signature-256: sha256=<calculated-signature>" \
  -d '{
    "order_id": "12345",
    "status": "confirmed",
    "total": 99.99
  }'
```

**Signature Calculation Example (Python)**
```python
import hmac
import hashlib
import json

def calculate_signature(payload, secret_key):
    # Create canonical payload string (sorted keys, compact)
    canonical_payload = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    
    # Create signature using HMAC-SHA256
    signature = hmac.new(
        key=secret_key.encode('utf-8'),
        msg=canonical_payload.encode('utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return f"sha256={signature}"

# Example usage
payload = {
    "order_id": "12345",
    "status": "confirmed",
    "total": 99.99
}
secret_key = "my-subscription-secret-key"
signature = calculate_signature(payload, secret_key)
print(f"X-Hub-Signature-256: {signature}")
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

Estimated monthly costs using free-tier cloud services (Railway.com):

| Service | Specs | Monthly Usage | Free Tier | Cost |
|---------|-------|---------------|-----------|------|
| Web Service | 0.1 CPU, 512MB RAM | 720 hours | 750 hours/month | $0 |
| PostgreSQL | 1GB storage | ~500MB data + indexes | 1GB free | $0 |
| Redis | 25MB memory | ~15MB | Not in free tier | $7/month |
| Worker | 0.1 CPU, 512MB RAM | 720 hours | Not in free tier | $7/month |
| **Total** | | | | **$14/month** |

Additional considerations:
- Bandwidth: Free tier includes ~100GB outbound transfer, which is sufficient for our payload sizes
- Log storage: Retention of 72 hours minimizes storage requirements
- Scaling: Additional workers would be needed if webhook volume grows significantly

## Assumptions

1. **Webhook Payload Size**: Average payload size is assumed to be under 10KB.
2. **Latency Requirements**: The system assumes that webhook delivery doesn't need real-time guarantees (async delivery with potential seconds of delay is acceptable).
3. **Response Time**: Target webhook endpoints are expected to respond within 10 seconds.
4. **Idempotency**: External endpoints should be idempotent to handle potential duplicate deliveries.
5. **Authentication**: The system doesn't handle OAuth or other complex authentication methods for target endpoints.
6. **Rate Limiting**: No specific rate limiting is implemented for individual target endpoints.

## Credits

### Libraries and Technologies
- [FastAPI](https://fastapi.tiangolo.com/) - Web framework
- [Celery](https://docs.celeryproject.org/) - Distributed task queue
- [SQLAlchemy](https://www.sqlalchemy.org/) - Database ORM
- [Redis](https://redis.io/) - Cache and message broker
- [PostgreSQL](https://www.postgresql.org/) - Database
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [Alembic](https://alembic.sqlalchemy.org/) - Database migrations
- [httpx](https://www.python-httpx.org/) - HTTP client for webhook delivery
- [uvicorn](https://www.uvicorn.org/) - ASGI server

### Tools
- Claude AI - Documentation assistance