#!/usr/bin/env python3
"""
Script to start Uvicorn server with proper logging configuration.
This ensures Uvicorn logs go to their own file separate from Celery logs.
"""
import os
import logging
import uvicorn
import argparse

# Define the absolute base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('uvicorn_starter')

def main():
    # Create logs directory if it doesn't exist
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Start Uvicorn server with configured logging')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload')
    args = parser.parse_args()
    
    # Configure log file
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": "uvicorn.logging.DefaultFormatter",
                "fmt": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "default": {
                "formatter": "default",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
            "file": {
                "formatter": "default",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.join(LOGS_DIR, 'uvicorn.log'),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["default", "file"], "level": "INFO"},
            "uvicorn.error": {"handlers": ["default", "file"], "level": "INFO", "propagate": False},
            "uvicorn.access": {"handlers": ["default", "file"], "level": "INFO", "propagate": False},
        },
    }
    
    logger.info(f"Starting Uvicorn server on {args.host}:{args.port}")
    
    # Start Uvicorn with configured logging
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_config=log_config
    )

if __name__ == "__main__":
    main() 