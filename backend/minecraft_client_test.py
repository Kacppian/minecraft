#!/usr/bin/env python3
"""
Test client for Minecraft WebSocket server
"""
import asyncio
import websockets
import json
import logging
import uuid
import time
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MinecraftTestClient")

# Set WebSocket URL
WS_URL = "ws://localhost:8001/ws"

class MinecraftTestClient:
    def __init__(self, name=None):
        self.id = str(uuid.uuid4())
        self.name = name or f"Player-{self.id[:5]}"
        self.connected = False
        self.ws = None
        self.position = {"x": 32, "y": 32, "z": 32}
        self.rotation = {"x": 0, "y": 0, "z": 0}
    
    async def connect(self):
        """Connect to the WebSocket server"""
        try:
            logger.info(f"Connecting client {self.name} ({self.id})...")
            self.ws = await websockets.connect(f"{WS_URL}/{self.id}")
            self.connected = True
            
            # Send initial connect message with player name
            await self.ws.send(json.dumps({
                "type": "connect",
                "name": self.name
            }))
            logger.info(f"Sent initial connect message with name: {self.name}")
            
            # Start message receiver
            asyncio.create_task(self.receive_messages())
            
            return True
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the server"""
        if self.ws and self.connected:
            await self.ws.close()
            self.connected = False
            logger.info(f"Disconnected client {self.name}")
    
    async def receive_messages(self):
        """Receive and log messages from the server"""
        try:
            while self.connected:
                message = await self.ws.recv()
                parsed = json.loads(message)
                logger.info(f"Received: {parsed}")
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection closed for {self.name}")
            self.connected = False
        except Exception as e:
            logger.error(f"Error in message receiver: {str(e)}")
            self.connected = False
    
    async def update_position(self):
        """Update position randomly"""
        if not self.connected:
            return False
        
        # Make a small random movement
        dx = random.uniform(-1, 1)
        dy = random.uniform(-0.2, 0.2)
        dz = random.uniform(-1, 1)
        
        self.position["x"] += dx
        self.position["y"] += dy
        self.position["z"] += dz
        
        try:
            await self.ws.send(json.dumps({
                "type": "position_update",
                "position": self.position
            }))
            logger.info(f"Sent position update: {self.position}")
            return True
        except Exception as e:
            logger.error(f"Failed to send position update: {str(e)}")
            return False
    
    async def update_rotation(self):
        """Update rotation randomly"""
        if not self.connected:
            return False
        
        # Make a small random rotation
        dx = random.uniform(-5, 5)
        dy = random.uniform(-5, 5)
        dz = random.uniform(-1, 1)
        
        self.rotation["x"] += dx
        self.rotation["y"] += dy
        self.rotation["z"] += dz
        
        try:
            await self.ws.send(json.dumps({
                "type": "rotation_update",
                "rotation": self.rotation
            }))
            logger.info(f"Sent rotation update: {self.rotation}")
            return True
        except Exception as e:
            logger.error(f"Failed to send rotation update: {str(e)}")
            return False
    
    async def place_block(self):
        """Place a random block"""
        if not self.connected:
            return False
        
        # Place a block near current position
        x = int(self.position["x"] + random.randint(-3, 3))
        y = int(self.position["y"] + random.randint(-3, 3))
        z = int(self.position["z"] + random.randint(-3, 3))
        block_id = random.randint(1, 5)  # Random block type
        
        try:
            await self.ws.send(json.dumps({
                "type": "block_update",
                "data": {
                    "action": "add",
                    "x": x,
                    "y": y,
                    "z": z,
                    "blockId": block_id
                }
            }))
            logger.info(f"Placed block {block_id} at ({x}, {y}, {z})")
            return True
        except Exception as e:
            logger.error(f"Failed to send block placement: {str(e)}")
            return False
    
    async def remove_block(self):
        """Remove a random block"""
        if not self.connected:
            return False
        
        # Remove a block near current position
        x = int(self.position["x"] + random.randint(-3, 3))
        y = int(self.position["y"] + random.randint(-3, 3))
        z = int(self.position["z"] + random.randint(-3, 3))
        
        try:
            await self.ws.send(json.dumps({
                "type": "block_update",
                "data": {
                    "action": "remove",
                    "x": x,
                    "y": y,
                    "z": z
                }
            }))
            logger.info(f"Removed block at ({x}, {y}, {z})")
            return True
        except Exception as e:
            logger.error(f"Failed to send block removal: {str(e)}")
            return False


async def run_multiple_clients():
    """Run multiple Minecraft test clients"""
    # Create two clients
    client1 = MinecraftTestClient("Steve")
    client2 = MinecraftTestClient("Alex")
    
    # Connect both clients
    await client1.connect()
    await asyncio.sleep(1)  # Wait a bit before connecting second client
    await client2.connect()
    
    # Let them exchange initial messages
    await asyncio.sleep(2)
    
    # Run a series of interactions
    for _ in range(5):
        # Client 1 moves and rotates
        await client1.update_position()
        await client1.update_rotation()
        await asyncio.sleep(0.5)
        
        # Client 2 moves and rotates
        await client2.update_position()
        await client2.update_rotation()
        await asyncio.sleep(0.5)
        
        # Client 1 places a block
        await client1.place_block()
        await asyncio.sleep(0.5)
        
        # Client 2 removes a block
        await client2.remove_block()
        await asyncio.sleep(0.5)
    
    # Let messages propagate
    await asyncio.sleep(2)
    
    # Disconnect client 1 first
    await client1.disconnect()
    await asyncio.sleep(1)
    
    # Then disconnect client 2
    await client2.disconnect()
    
    logger.info("Test completed successfully")

if __name__ == "__main__":
    logger.info("Starting Minecraft WebSocket test")
    asyncio.run(run_multiple_clients())