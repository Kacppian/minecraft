#!/usr/bin/env python3
"""
Simple WebSocket client for testing
"""
import asyncio
import websockets
import json
import logging
import uuid
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimpleClient")

# Set WebSocket URL
WS_URL = "ws://localhost:8002/ws"

async def run_client():
    """Run a simple WebSocket client"""
    client_id = str(uuid.uuid4())
    logger.info(f"Client ID: {client_id}")
    logger.info(f"Connecting to {WS_URL}/{client_id}")
    
    try:
        # Connect to the WebSocket
        async with websockets.connect(f"{WS_URL}/{client_id}") as ws:
            logger.info("Connected successfully!")
            
            # Listen for messages in a separate task
            receiver_task = asyncio.create_task(message_receiver(ws))
            
            # Send a ping message
            await ws.send(json.dumps({
                "type": "ping",
                "timestamp": time.time()
            }))
            logger.info("Sent ping message")
            
            # Send a chat message
            await ws.send(json.dumps({
                "type": "chat",
                "message": "Hello, WebSocket server!"
            }))
            logger.info("Sent chat message")
            
            # Wait for a while to receive messages
            await asyncio.sleep(10)
            
            # Cancel the receiver task
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass
            
            logger.info("Test completed successfully")
            return True
    except Exception as e:
        logger.error(f"Error: {type(e).__name__}: {str(e)}")
        return False

async def message_receiver(websocket):
    """Receive and log messages from the WebSocket"""
    try:
        while True:
            message = await websocket.recv()
            logger.info(f"Received: {message}")
    except asyncio.CancelledError:
        logger.info("Receiver task cancelled")
        raise
    except Exception as e:
        logger.error(f"Error in receiver: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting WebSocket client test")
    result = asyncio.run(run_client())
    exit(0 if result else 1)