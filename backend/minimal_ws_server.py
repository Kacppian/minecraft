#!/usr/bin/env python3
"""
Minimal WebSocket server for testing WebSocket connections
"""
import asyncio
import websockets
import json
import logging
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MinimalWSServer")

app = FastAPI()

# Active connections
connections = {}

@app.get("/")
async def root():
    return {"message": "Minimal WebSocket Server", "connections": len(connections)}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    logger.info(f"Client connected: {client_id}")
    
    # Store the connection
    connections[client_id] = websocket
    
    # Send welcome message
    await websocket.send_text(json.dumps({
        "type": "welcome",
        "message": f"Welcome, {client_id}!"
    }))
    
    # Broadcast to all other clients that a new client has joined
    for cid, conn in connections.items():
        if cid != client_id:
            try:
                await conn.send_text(json.dumps({
                    "type": "client_joined",
                    "client_id": client_id
                }))
                logger.info(f"Notified {cid} about {client_id} joining")
            except Exception as e:
                logger.error(f"Error notifying {cid}: {str(e)}")
    
    try:
        # Echo anything received back to all clients
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received from {client_id}: {data}")
            
            # Echo to all clients
            for cid, conn in connections.items():
                try:
                    await conn.send_text(json.dumps({
                        "type": "message",
                        "from": client_id,
                        "data": data
                    }))
                    logger.info(f"Sent message from {client_id} to {cid}")
                except Exception as e:
                    logger.error(f"Error sending to {cid}: {str(e)}")
    
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
        if client_id in connections:
            del connections[client_id]
            
            # Notify all clients that this client has left
            for cid, conn in connections.items():
                try:
                    await conn.send_text(json.dumps({
                        "type": "client_left",
                        "client_id": client_id
                    }))
                    logger.info(f"Notified {cid} about {client_id} leaving")
                except Exception as e:
                    logger.error(f"Error notifying {cid}: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting minimal WebSocket server...")
    uvicorn.run(app, host="0.0.0.0", port=8005)