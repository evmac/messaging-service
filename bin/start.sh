#!/bin/bash

# I would recommend Dockerizing the application, but I kept the script as per the instructions for now.

set -e

echo "Starting the application..."
echo "Environment: ${ENV:-development}"

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Start the FastAPI application
echo "Starting FastAPI server on ${HOST:-0.0.0.0}:${PORT:-8000}"
uvicorn app.main:app --host ${HOST:-0.0.0.0} --port ${PORT:-8000}

# Deactivate virtual environment
echo "Deactivating virtual environment..."
deactivate
