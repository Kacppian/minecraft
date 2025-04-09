#!/usr/bin/env python3
"""
Simple WebSocket connection test
"""
import asyncio
import websockets
import json
import logging
import uuid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimpleTest")

# Set WebSocket URL
WS_URL = "ws://localhost:8001/ws"

async def test_simple_connection():
    """Test a simple WebSocket connection"""
    player_id = str(uuid.uuid4())
    logger.info(f"Connecting to {WS_URL}/{player_id}")
    
    try:
        # Connect to the WebSocket
        async with websockets.connect(f"{WS_URL}/{player_id}") as ws:
            logger.info("Connected successfully!")
            
            # Send player name
            await ws.send(json.dumps({
                "type": "connect",
                "name": "SimpleTestPlayer"
            }))
            logger.info("Sent player name")
            
            # Try to receive a message
            logger.info("Waiting for a message...")
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=5)
                logger.info(f"Received message: {message}")
                return True
            except asyncio.TimeoutError:
                logger.error("Timeout waiting for message")
                return False
    except Exception as e:
        logger.error(f"Connection failed: {type(e).__name__}: {str(e)}")
        return False

if __name__ == "__main__":
    logger.info("Starting simple WebSocket test")
    result = asyncio.run(test_simple_connection())
    exit(0 if result else 1)