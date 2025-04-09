#!/bin/bash

# Helper script to run WebSocket tests

# Install required dependencies
pip install pytest pytest-asyncio websockets

# Get the base URL from environment or use default
WS_URL=${1:-"ws://localhost:8000/ws"}

echo "Running WebSocket tests against: $WS_URL"
python3 test_websocket.py $WS_URL