#!/bin/bash
# Start the APIHub-Gateway backend server

cd "$(dirname "$0")"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -q

# Copy .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Start the server
echo "Starting APIHub-Gateway backend..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
