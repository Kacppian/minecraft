#!/usr/bin/env python3
"""
Minimal WebSocket client for testing WebSocket connections
"""
import asyncio
import websockets
import json
import logging
import uuid
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MinimalWSClient")

# Default server URL
SERVER_URL = "ws://localhost:8005/ws"

async def client(name):
    """Connect to WebSocket server and exchange messages"""
    client_id = name + "-" + str(uuid.uuid4())[:8]
    uri = f"{SERVER_URL}/{client_id}"
    
    logger.info(f"[{name}] Connecting to {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            logger.info(f"[{name}] Connected successfully")
            
            # Send a hello message
            message = {
                "type": "hello",
                "name": name
            }
            await websocket.send(json.dumps(message))
            logger.info(f"[{name}] Sent: {message}")
            
            # Simple message receiver
            async def receive_messages():
                while True:
                    try:
                        message = await websocket.recv()
                        logger.info(f"[{name}] Received: {message}")
                    except websockets.exceptions.ConnectionClosed:
                        logger.info(f"[{name}] Connection closed")
                        break
                    except Exception as e:
                        logger.error(f"[{name}] Error receiving message: {e}")
                        break
            
            # Start receiver task
            receiver_task = asyncio.create_task(receive_messages())
            
            # Send a few messages
            for i in range(3):
                message = {
                    "type": "message",
                    "content": f"Message {i+1} from {name}"
                }
                await websocket.send(json.dumps(message))
                logger.info(f"[{name}] Sent: {message}")
                await asyncio.sleep(1)
            
            # Keep connection open for a while
            await asyncio.sleep(10)
            
            # Cancel receiver task
            receiver_task.cancel()
            
            logger.info(f"[{name}] Disconnecting")
    
    except Exception as e:
        logger.error(f"[{name}] Connection error: {e}")

async def main():
    """Run multiple clients"""
    if len(sys.argv) > 1:
        global SERVER_URL
        SERVER_URL = sys.argv[1]
    
    logger.info(f"Using server URL: {SERVER_URL}")
    
    # Run two clients concurrently
    await asyncio.gather(
        client("ClientA"),
        client("ClientB")
    )

if __name__ == "__main__":
    asyncio.run(main())