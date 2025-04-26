"""
Background workers and Celery tasks.
"""
from app.workers.celery_app import celery_app

# Avoid importing tasks directly to prevent circular imports
# Task registry will be handled by Celery discovery