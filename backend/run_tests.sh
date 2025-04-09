#!/bin/bash

# Install required dependencies
pip install websockets

# Set default WebSocket URL
WS_URL=${1:-"ws://localhost:8000/ws"}

echo "Running WebSocket tests against: $WS_URL"
python3 test_websockets.py $WS_URL