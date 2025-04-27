#!/usr/bin/env python3
"""
Script to start Celery worker with proper logging configuration.
This script ensures Celery logs go to their own file instead of mixing with Uvicorn logs.
"""
import os
import logging
import subprocess
from logging.handlers import RotatingFileHandler

# Define the absolute base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Configure Celery environment
os.environ.setdefault('CELERY_CONFIG_MODULE', 'app.workers.celery_app')

# Configure logging for this script
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('celery_starter')

def setup_logging():
    """Set up proper logging for Celery to output to a dedicated file."""
    # Create logs directory if it doesn't exist
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Configure rotating file handler for Celery logs
    log_file = os.path.join(LOGS_DIR, 'celery.log')
    
    # Configure the root logger to write to the file
    logger.info(f"Configuring Celery logging to: {log_file}")
    
    return log_file

def start_celery_worker():
    """Start the Celery worker process with proper logging configuration."""
    log_file = setup_logging()
    
    # Construct the Celery command
    cmd = [
        'celery',
        '-A', 'app.workers.celery_app',
        'worker',
        '--loglevel=INFO',
        '--logfile', log_file,
        '--without-gossip',
        '--without-mingle'
    ]
    
    logger.info("Starting Celery worker...")
    logger.info(f"Running command: {' '.join(cmd)}")
    
    # Run the Celery worker, redirecting stdout/stderr to the log file
    with open(log_file, 'a') as log_fh:
        process = subprocess.Popen(
            cmd,
            stdout=log_fh,
            stderr=log_fh
        )
        
    logger.info(f"Celery worker started with PID: {process.pid}")
    return process

if __name__ == "__main__":
    process = start_celery_worker() 