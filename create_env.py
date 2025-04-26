#!/usr/bin/env python
"""Create a minimal .env file for development."""

with open(".env", "w") as f:
    f.write("""DEBUG=true
SECRET_KEY=webhook
DATABASE_URL=postgresql+asyncpg://postgres:webhookService@db.nfvukxumzzlxvacimvbe.supabase.co:5432/postgres
SYNC_DATABASE_URL=postgresql://postgres:webhookService@db.nfvukxumzzlxvacimvbe.supabase.co:5432/postgres
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CORS_ORIGINS=http://localhost:8000,http://localhost:3000
""") 