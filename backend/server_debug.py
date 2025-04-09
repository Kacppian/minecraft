from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import logging
import asyncio
import uuid
from typing import Dict

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Use DEBUG level to see all messages
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebSocketServer")

# Create FastAPI app
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active connections
active_connections: Dict[str, WebSocket] = {}

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Hello World"}

@app.get("/status")
async def status():
    logger.info("Status endpoint called")
    return {
        "status": "online",
        "connections": len(active_connections),
        "connection_ids": list(active_connections.keys())
    }

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    logger.info(f"WebSocket connection request from {client_id}")
    
    # Accept connection
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for {client_id}")
    
    # Store connection
    active_connections[client_id] = websocket
    
    try:
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "welcome",
            "message": f"Welcome to the WebSocket server, {client_id}!",
            "id": client_id
        }))
        logger.info(f"Sent welcome message to {client_id}")
        
        # Broadcast connection notification to other clients
        for cid, conn in active_connections.items():
            if cid != client_id:
                try:
                    await conn.send_text(json.dumps({
                        "type": "user_joined",
                        "id": client_id
                    }))
                    logger.info(f"Sent join notification to {cid}")
                except Exception as e:
                    logger.error(f"Error sending join notification to {cid}: {str(e)}")
        
        # Listen for messages
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received message from {client_id}: {data}")
            
            try:
                message = json.loads(data)
                message_type = message.get("type", "")
                
                if message_type == "ping":
                    # Respond to ping
                    await websocket.send_text(json.dumps({
                        "type": "pong",
                        "timestamp": message.get("timestamp", 0)
                    }))
                    logger.info(f"Sent pong to {client_id}")
                
                elif message_type == "chat":
                    # Broadcast chat message
                    chat_message = message.get("message", "")
                    for cid, conn in active_connections.items():
                        if cid != client_id:
                            try:
                                await conn.send_text(json.dumps({
                                    "type": "chat",
                                    "from": client_id,
                                    "message": chat_message
                                }))
                                logger.info(f"Forwarded chat message to {cid}")
                            except Exception as e:
                                logger.error(f"Error forwarding chat message to {cid}: {str(e)}")
                
                # Echo all messages back for testing
                await websocket.send_text(json.dumps({
                    "type": "echo",
                    "original": message
                }))
                logger.info(f"Sent echo to {client_id}")
                
            except json.JSONDecodeError:
                logger.warning(f"Received invalid JSON from {client_id}")
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON"
                }))
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {client_id}")
    except Exception as e:
        logger.error(f"Error in WebSocket connection for {client_id}: {str(e)}")
    finally:
        # Remove connection
        if client_id in active_connections:
            del active_connections[client_id]
        
        # Broadcast disconnection notification
        for cid, conn in active_connections.items():
            try:
                await conn.send_text(json.dumps({
                    "type": "user_left",
                    "id": client_id
                }))
                logger.info(f"Sent leave notification to {cid}")
            except Exception as e:
                logger.error(f"Error sending leave notification to {cid}: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting WebSocket server")
    uvicorn.run(app, host="0.0.0.0", port=8001)