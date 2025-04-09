from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import uvicorn
import os
import logging
import json
from pathlib import Path
from typing import Dict, List

# /backend 
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

app = FastAPI()  # No prefix for local testing

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Store active connections
class ConnectionManager:
    def __init__(self):
        # active_connections is a dict of websocket connections with player_id as key
        self.active_connections: Dict[str, WebSocket] = {}
        # Store player states (position, rotation, etc.)
        self.player_states: Dict[str, dict] = {}
        # Last time we logged debug info
        self.last_debug_log = 0
        
    async def connect(self, websocket: WebSocket, player_id: str, player_name: str):
        await websocket.accept()
        self.active_connections[player_id] = websocket
        # Initialize player state
        self.player_states[player_id] = {
            "id": player_id,
            "name": player_name,
            "position": {"x": 32, "y": 32, "z": 32},
            "rotation": {"x": 0, "y": 0, "z": 0},
            "connected": True
        }
        
        # First send existing players data to the new player
        await self.send_existing_players(player_id)
        
        # Then notify all clients about the new player
        await self.broadcast_player_joined(player_id)
        
        logger.info(f"Player {player_name} ({player_id}) connected. Total players: {len(self.active_connections)}")
        
    def disconnect(self, player_id: str):
        if player_id in self.active_connections:
            del self.active_connections[player_id]
            # Mark player as disconnected but keep state for a while
            if player_id in self.player_states:
                self.player_states[player_id]["connected"] = False
            logger.info(f"Player {player_id} disconnected. Total players: {len(self.active_connections)}")
    
    async def send_existing_players(self, player_id: str):
        """Send all existing player states to a newly connected player"""
        if player_id in self.active_connections:
            existing_players = {pid: state for pid, state in self.player_states.items() 
                               if pid != player_id and state["connected"]}
            if existing_players:
                await self.active_connections[player_id].send_text(
                    json.dumps({
                        "type": "existing_players",
                        "players": list(existing_players.values())
                    })
                )
    
    async def broadcast_player_joined(self, player_id: str):
        """Notify all clients about a new player"""
        if player_id in self.player_states:
            for connection_id, connection in self.active_connections.items():
                if connection_id != player_id:  # Don't send to the player who just joined
                    await connection.send_text(
                        json.dumps({
                            "type": "player_joined",
                            "player": self.player_states[player_id]
                        })
                    )
    
    async def broadcast_player_left(self, player_id: str):
        """Notify all clients when a player leaves"""
        for connection_id, connection in self.active_connections.items():
            if connection_id != player_id:  # Don't send to the player who left
                await connection.send_text(
                    json.dumps({
                        "type": "player_left",
                        "player_id": player_id
                    })
                )
    
    async def update_player_state(self, player_id: str, update_data: dict):
        """Update player state and broadcast to other players"""
        if player_id in self.player_states:
            # Update specific fields
            for key, value in update_data.items():
                if key in ["position", "rotation"]:
                    for coord, val in value.items():
                        self.player_states[player_id][key][coord] = val
            
            # Broadcast to all other players
            for connection_id, connection in self.active_connections.items():
                if connection_id != player_id:  # Don't send back to the player who made the update
                    await connection.send_text(
                        json.dumps({
                            "type": "player_state_update",
                            "player_id": player_id,
                            "state": update_data
                        })
                    )

    async def broadcast_block_update(self, player_id: str, block_data: dict):
        """Broadcast block updates to all players except the one who made the change"""
        for connection_id, connection in self.active_connections.items():
            if connection_id != player_id:
                await connection.send_text(
                    json.dumps({
                        "type": "block_update",
                        "data": block_data
                    })
                )

# Initialize connection manager
manager = ConnectionManager()

@app.get("/")
async def root():
    logger.info("Root endpoint called")
    return {"message": "Hello World"}

@app.get("/test")
async def test():
    logger.info("Test endpoint called")
    return {"status": "ok", "active_connections": len(manager.active_connections)}

@app.get("/api/test")
async def api_test():
    logger.info("API test endpoint called")
    return {"status": "ok", "message": "API endpoint works", "active_connections": len(manager.active_connections)}

@app.get("/api/ws/test")
async def ws_path_test():
    logger.info("WebSocket path test endpoint called")
    return {"status": "ok", "message": "WebSocket path works"}

@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    """WebSocket endpoint for direct access without /api prefix"""
    # First, accept the connection
    logger.info(f"WebSocket connection request from player {player_id}")
    try:
        await websocket.accept()
        logger.info(f"WebSocket connection accepted for player {player_id}")
    except Exception as e:
        logger.error(f"Failed to accept WebSocket connection: {str(e)}")
        return
    
    try:
        # First message should contain player name
        try:
            data = await websocket.receive_text()
            connection_data = json.loads(data)
            player_name = connection_data.get("name", f"Player-{player_id[:5]}")
            logger.info(f"Received initial message with player name: {player_name}")
        except Exception as e:
            logger.error(f"Failed to receive initial player data: {str(e)}")
            player_name = f"Player-{player_id[:5]}"
        
        # Complete connection with player info
        try:
            await manager.connect(websocket, player_id, player_name)
        except Exception as e:
            logger.error(f"Failed to register player in manager: {str(e)}")
            return
        
        # Handle incoming messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                message_type = message.get("type", "")
                
                logger.info(f"Received message from {player_name} ({player_id}): {message_type}")
                
                if message_type == "position_update":
                    position = message.get("position", {})
                    if all(k in position for k in ["x", "y", "z"]):
                        await manager.update_player_state(player_id, {"position": position})
                    else:
                        logger.warning(f"Invalid position data from {player_id}: {position}")
                
                elif message_type == "rotation_update":
                    rotation = message.get("rotation", {})
                    if all(k in rotation for k in ["x", "y", "z"]):
                        await manager.update_player_state(player_id, {"rotation": rotation})
                    else:
                        logger.warning(f"Invalid rotation data from {player_id}: {rotation}")
                
                elif message_type == "block_update":
                    block_data = message.get("data", {})
                    if "action" in block_data and "x" in block_data and "y" in block_data and "z" in block_data:
                        await manager.broadcast_block_update(player_id, block_data)
                    else:
                        logger.warning(f"Invalid block_update data from {player_id}: {block_data}")
                
                # Add more message types as needed
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {player_id}")
            except WebSocketDisconnect:
                logger.info(f"Connection closed for {player_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message from {player_id}: {str(e)}")
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for player {player_id}")
    except Exception as e:
        logger.error(f"WebSocket error for player {player_id}: {str(e)}")
    finally:
        # Always ensure player is disconnected properly
        try:
            manager.disconnect(player_id)
            await manager.broadcast_player_left(player_id)
            logger.info(f"Player {player_id} properly disconnected and broadcast sent")
        except Exception as e:
            logger.error(f"Error during disconnect cleanup: {str(e)}")

@app.websocket("/api/ws/{player_id}")
async def api_websocket_endpoint(websocket: WebSocket, player_id: str):
    """WebSocket endpoint with /api prefix for production environment"""
    await websocket_endpoint(websocket, player_id)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

