#!/usr/bin/env python3
"""
Start both Uvicorn and Celery services with proper logging configurations.
This ensures each service logs to its own file.
"""
import os
import sys
import logging
import subprocess
import time
import signal
import argparse

# Define the absolute base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Create logs directory if it doesn't exist
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOGS_DIR, 'services.log'))
    ]
)
logger = logging.getLogger('service_starter')

# Track child processes
processes = []

def signal_handler(sig, frame):
    """Handle termination signals to gracefully shut down all processes."""
    logger.info("Shutting down all services...")
    for p in processes:
        if p.poll() is None:  # If process is still running
            logger.info(f"Terminating process with PID {p.pid}")
            p.terminate()
    
    # Give processes time to terminate gracefully
    time.sleep(2)
    
    # Force kill any remaining processes
    for p in processes:
        if p.poll() is None:
            logger.info(f"Force killing process with PID {p.pid}")
            p.kill()
    
    logger.info("All services shut down")
    sys.exit(0)

def start_uvicorn(host, port, reload):
    """Start the Uvicorn server process."""
    cmd = [
        sys.executable, 'start_uvicorn.py',
        '--host', host,
        '--port', str(port)
    ]
    
    if reload:
        cmd.append('--reload')
    
    logger.info(f"Starting Uvicorn server: {' '.join(cmd)}")
    process = subprocess.Popen(cmd)
    logger.info(f"Uvicorn server started with PID: {process.pid}")
    return process

def start_celery():
    """Start the Celery worker process."""
    cmd = [sys.executable, 'start_celery.py']
    
    logger.info(f"Starting Celery worker: {' '.join(cmd)}")
    process = subprocess.Popen(cmd)
    logger.info(f"Celery worker started with PID: {process.pid}")
    return process

def main():
    """Main function to parse arguments and start services."""
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Start Webhook Delivery Service')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload for Uvicorn')
    parser.add_argument('--uvicorn-only', action='store_true', help='Start only the Uvicorn server')
    parser.add_argument('--celery-only', action='store_true', help='Start only the Celery worker')
    args = parser.parse_args()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start the requested services
        if args.celery_only:
            processes.append(start_celery())
        elif args.uvicorn_only:
            processes.append(start_uvicorn(args.host, args.port, args.reload))
        else:
            # Start both services
            processes.append(start_uvicorn(args.host, args.port, args.reload))
            processes.append(start_celery())
        
        logger.info("All services started successfully")
        
        # Keep the script running to maintain the child processes
        while all(p.poll() is None for p in processes):
            time.sleep(1)
        
        # Check if any process exited unexpectedly
        for p in processes:
            if p.poll() is not None:
                logger.error(f"Process with PID {p.pid} exited with code {p.returncode}")
        
        # Terminate any remaining processes
        signal_handler(None, None)
        
    except Exception as e:
        logger.exception(f"Error starting services: {e}")
        signal_handler(None, None)
        sys.exit(1)

if __name__ == "__main__":
    main() 