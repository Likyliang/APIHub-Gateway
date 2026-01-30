#!/bin/bash
# Start the APIHub-Gateway frontend

cd "$(dirname "$0")"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the dev server
echo "Starting APIHub-Gateway frontend..."
npm run dev
