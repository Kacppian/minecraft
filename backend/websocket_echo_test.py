#!/usr/bin/env python3
"""
Simple WebSocket echo test to verify bidirectional communication.
This creates two clients and verifies they can see each other's messages.
"""

import asyncio
import websockets
import json
import uuid
import logging
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EchoTest")

# Default WebSocket server URL - adjust the port if needed
WS_SERVER_URL = "ws://localhost:8001/ws"

class TestClient:
    def __init__(self, name):
        self.id = str(uuid.uuid4())
        self.name = name
        self.ws = None
        self.messages_received = []
        self.connected = False
    
    async def connect(self):
        """Connect to WebSocket server"""
        try:
            ws_url = f"{WS_SERVER_URL}/{self.id}"
            logger.info(f"[{self.name}] Connecting to: {ws_url}")
            self.ws = await websockets.connect(ws_url)
            self.connected = True
            
            # Send initial connect message
            await self.send_message({
                "type": "connect",
                "name": self.name
            })
            logger.info(f"[{self.name}] Connected and sent initial message")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket server"""
        if self.ws and self.connected:
            await self.ws.close()
            self.connected = False
            logger.info(f"[{self.name}] Disconnected")
    
    async def send_message(self, message):
        """Send a message to the WebSocket server"""
        if not self.ws or not self.connected:
            logger.error(f"[{self.name}] Cannot send message: Not connected")
            return False
        
        try:
            await self.ws.send(json.dumps(message))
            logger.info(f"[{self.name}] Sent: {message}")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Failed to send message: {e}")
            return False
    
    async def listen(self, timeout=5.0):
        """Listen for messages for a specified duration"""
        if not self.ws or not self.connected:
            logger.error(f"[{self.name}] Cannot listen: Not connected")
            return False
        
        end_time = time.time() + timeout
        try:
            while time.time() < end_time:
                try:
                    # Set a short timeout to allow checking if we've reached the end time
                    message = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
                    parsed = json.loads(message)
                    self.messages_received.append(parsed)
                    logger.info(f"[{self.name}] Received: {parsed}")
                except asyncio.TimeoutError:
                    # This is expected since we're using a short timeout
                    continue
                except Exception as e:
                    logger.error(f"[{self.name}] Error receiving message: {e}")
            
            logger.info(f"[{self.name}] Finished listening. Received {len(self.messages_received)} messages.")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Listening error: {e}")
            return False
    
    def has_received_from(self, other_client_id, message_type=None):
        """Check if client has received a message from the other client"""
        for msg in self.messages_received:
            # Check for player_joined messages
            if message_type == "player_joined" and msg.get("type") == "player_joined":
                if msg.get("player", {}).get("id") == other_client_id:
                    return True
            
            # Check for player_state_update messages
            elif message_type == "player_state_update" and msg.get("type") == "player_state_update":
                if msg.get("player_id") == other_client_id:
                    return True
            
            # Check for existing_players messages containing the other client
            elif message_type == "existing_players" and msg.get("type") == "existing_players":
                for player in msg.get("players", []):
                    if player.get("id") == other_client_id:
                        return True
            
            # Generic check for any message that mentions the other client
            elif message_type is None:
                if (msg.get("player_id") == other_client_id or 
                    msg.get("player", {}).get("id") == other_client_id):
                    return True
                
                # Check players list in existing_players message
                if msg.get("type") == "existing_players":
                    for player in msg.get("players", []):
                        if player.get("id") == other_client_id:
                            return True
        
        return False

async def run_test():
    """Run the WebSocket echo test with two clients"""
    logger.info("Starting WebSocket echo test")
    
    # Create two test clients
    client1 = TestClient("Player1Test")
    client2 = TestClient("Player2Test")
    
    # Connect client 1
    logger.info("==== Step 1: Connect first client ====")
    if not await client1.connect():
        logger.error("Failed to connect first client")
        return False
    
    # Wait a moment to stabilize the connection
    await asyncio.sleep(1)
    
    # Listen for any initial messages from the server
    logger.info("==== Step 2: Listen for initial messages (client1) ====")
    await client1.listen(timeout=2)
    logger.info(f"Client1 received {len(client1.messages_received)} initial messages")
    
    # Connect client 2
    logger.info("==== Step 3: Connect second client ====")
    if not await client2.connect():
        logger.error("Failed to connect second client")
        await client1.disconnect()
        return False
    
    # Listen for messages from the server on client 2
    logger.info("==== Step 4: Listen for initial messages (client2) ====")
    await client2.listen(timeout=2)
    logger.info(f"Client2 received {len(client2.messages_received)} initial messages")
    
    # Listen on client 1 for notifications about client 2
    logger.info("==== Step 5: Check if client1 is aware of client2 ====")
    client1.messages_received = []  # Clear previous messages
    await client1.listen(timeout=3)
    
    if client1.has_received_from(client2.id):
        logger.info("✓ Client1 received messages about Client2")
    else:
        logger.error("✗ Client1 did NOT receive any messages about Client2")
    
    # Send position update from client 1
    logger.info("==== Step 6: Send position update from client1 ====")
    await client1.send_message({
        "type": "position_update",
        "position": {"x": 123.45, "y": 67.89, "z": 12.34}
    })
    
    # Listen on client 2 for updates from client 1
    logger.info("==== Step 7: Check if client2 receives position update from client1 ====")
    client2.messages_received = []  # Clear previous messages
    await client2.listen(timeout=3)
    
    if client2.has_received_from(client1.id, "player_state_update"):
        logger.info("✓ Client2 received position update from Client1")
    else:
        logger.error("✗ Client2 did NOT receive position update from Client1")
    
    # Send position update from client 2
    logger.info("==== Step 8: Send position update from client2 ====")
    await client2.send_message({
        "type": "position_update",
        "position": {"x": 98.76, "y": 54.32, "z": 10.11}
    })
    
    # Listen on client 1 for updates from client 2
    logger.info("==== Step 9: Check if client1 receives position update from client2 ====")
    client1.messages_received = []  # Clear previous messages
    await client1.listen(timeout=3)
    
    if client1.has_received_from(client2.id, "player_state_update"):
        logger.info("✓ Client1 received position update from Client2")
    else:
        logger.error("✗ Client1 did NOT receive position update from Client2")
    
    # Summary
    logger.info("==== Test Summary ====")
    logger.info(f"Client1 total messages: {len(client1.messages_received)}")
    logger.info(f"Client2 total messages: {len(client2.messages_received)}")
    
    # Disconnect both clients
    await client1.disconnect()
    await client2.disconnect()
    
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1:
        WS_SERVER_URL = sys.argv[1]
    
    logger.info(f"Using WebSocket server URL: {WS_SERVER_URL}")
    asyncio.run(run_test())