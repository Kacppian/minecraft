from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import uvicorn
import os
import logging
import json
import time
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
        # Don't call accept here - the endpoint should handle that
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
            
            logger.info(f"Sending existing players to {player_id}: {len(existing_players)} players")
            if existing_players:
                try:
                    await self.active_connections[player_id].send_text(
                        json.dumps({
                            "type": "existing_players",
                            "players": list(existing_players.values())
                        })
                    )
                    logger.info(f"Sent existing_players event to {player_id} with {len(existing_players)} players")
                except Exception as e:
                    logger.error(f"Error sending existing_players to {player_id}: {str(e)}")
            else:
                logger.info(f"No existing players to send to {player_id}")
    
    async def broadcast_player_joined(self, player_id: str):
        """Notify all clients about a new player"""
        if player_id in self.player_states:
            player_data = self.player_states[player_id]
            broadcast_count = 0
            
            logger.info(f"Broadcasting player joined event for {player_data['name']} ({player_id})")
            logger.info(f"Active connections: {len(self.active_connections)}, broadcasting to ALL players")
            
            # Broadcast to ALL connections, including the player who joined
            # The frontend will filter out messages about its own player
            for connection_id, connection in self.active_connections.items():
                try:
                    await connection.send_text(
                        json.dumps({
                            "type": "player_joined",
                            "player": player_data
                        })
                    )
                    logger.info(f"Sent player_joined event to {connection_id}")
                    broadcast_count += 1
                except Exception as e:
                    logger.error(f"Error sending player_joined event to {connection_id}: {str(e)}")
            
            if broadcast_count > 0:
                logger.info(f"Successfully broadcast player_joined event to {broadcast_count} players")
            else:
                logger.info("No players to broadcast join event to")
    
    async def broadcast_player_left(self, player_id: str):
        """Notify all clients when a player leaves"""
        logger.info(f"Broadcasting player_left event for {player_id}")
        broadcast_count = 0
        
        # Broadcast to all active connections
        for connection_id, connection in self.active_connections.items():
            try:
                await connection.send_text(
                    json.dumps({
                        "type": "player_left",
                        "player_id": player_id
                    })
                )
                logger.info(f"Sent player_left notification to {connection_id}")
                broadcast_count += 1
            except Exception as e:
                logger.error(f"Error sending player_left notification to {connection_id}: {str(e)}")
        
        logger.info(f"Successfully broadcast player_left event to {broadcast_count} players")
    
    async def update_player_state(self, player_id: str, update_data: dict):
        """Update player state and broadcast to other players"""
        if player_id in self.player_states:
            # Update specific fields
            for key, value in update_data.items():
                if key in ["position", "rotation"]:
                    for coord, val in value.items():
                        self.player_states[player_id][key][coord] = val
            
            # Broadcast to ALL players - the frontend will filter its own updates
            broadcast_count = 0
            for connection_id, connection in self.active_connections.items():
                try:
                    await connection.send_text(
                        json.dumps({
                            "type": "player_state_update",
                            "player_id": player_id,
                            "state": update_data
                        })
                    )
                    broadcast_count += 1
                except Exception as e:
                    logger.error(f"Error broadcasting state update to {connection_id}: {str(e)}")
            
            # Periodically log player states for debugging
            current_time = time.time()
            if current_time - self.last_debug_log > 10:  # Log every 10 seconds
                active_players = {pid: state for pid, state in self.player_states.items() 
                                if pid in self.active_connections}
                
                logger.info(f"Active connections: {len(self.active_connections)}, Active players: {len(active_players)}")
                if active_players:
                    for pid, state in active_players.items():
                        logger.info(f"Player {state['name']} ({pid}) - pos: {state['position']}")
                
                # Log broadcast info
                logger.info(f"Broadcast state update from {player_id} to {broadcast_count} players")
                
                self.last_debug_log = current_time

    async def broadcast_block_update(self, player_id: str, block_data: dict):
        """Broadcast block updates to all players"""
        for connection_id, connection in self.active_connections.items():
            try:
                await connection.send_text(
                    json.dumps({
                        "type": "block_update",
                        "data": block_data
                    })
                )
            except Exception as e:
                logger.error(f"Error broadcasting block update to {connection_id}: {str(e)}")

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
    logger.info("API Test endpoint called")
    return {"status": "ok", "active_connections": len(manager.active_connections), "prefix": "api"}

@app.websocket("/ws/{player_id}")
@app.websocket("/api/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: str):
    """WebSocket endpoint for both direct access and /api prefix"""
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
                
                elif message_type == "chat_message":
                    chat_text = message.get("text", "").strip()
                    if chat_text:
                        logger.info(f"Chat message from {player_name} ({player_id}): {chat_text}")
                        # Broadcast chat message to all players
                        for connection_id, connection in manager.active_connections.items():
                            try:
                                await connection.send_text(
                                    json.dumps({
                                        "type": "chat_message",
                                        "player_id": player_id,
                                        "text": chat_text
                                    })
                                )
                                logger.debug(f"Sent chat message to {connection_id}")
                            except Exception as e:
                                logger.error(f"Error sending chat message to {connection_id}: {str(e)}")
                    else:
                        logger.warning(f"Empty chat message from {player_id}")
                        
                elif message_type == "supersaiyan_toggle":
                    active = message.get("active", False)
                    logger.info(f"SuperSaiyan toggle from {player_name} ({player_id}): {active}")
                    # Broadcast SuperSaiyan toggle to all players
                    for connection_id, connection in manager.active_connections.items():
                        try:
                            await connection.send_text(
                                json.dumps({
                                    "type": "supersaiyan_toggle",
                                    "player_id": player_id,
                                    "active": active
                                })
                            )
                            logger.debug(f"Sent SuperSaiyan toggle to {connection_id}")
                        except Exception as e:
                            logger.error(f"Error sending SuperSaiyan toggle to {connection_id}: {str(e)}")
                
                # Add more message types as needed
                
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON from {player_id}")
            except WebSocketDisconnect:
                logger.info(f"Connection closed for {player_id}")
                break
            except Exception as e:
                logger.error(f"Error processing message from {player_id}: {str(e)}")
                if "Cannot call \"receive\" once a disconnect message has been received" in str(e):
                    logger.info(f"WebSocket already disconnected for {player_id}, breaking loop")
                    break
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

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)