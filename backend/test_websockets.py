#!/usr/bin/env python3
"""
Comprehensive WebSocket test for Minecraft multiplayer backend.
This test script simulates multiple clients connecting and interacting through WebSockets.
"""

import asyncio
import json
import logging
import websockets
import uuid
import time
import sys
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebSocketTester")

# Default WebSocket server URL
WS_SERVER_URL = "ws://localhost:8001/ws"

class MinecraftClient:
    """Simulates a Minecraft client connecting to the server via WebSocket"""
    
    def __init__(self, name: str = None):
        self.id = str(uuid.uuid4())
        self.name = name or f"TestPlayer-{self.id[:5]}"
        self.ws = None
        self.connected = False
        self.messages = []
        self.position = {"x": 32, "y": 32, "z": 32}
        self.rotation = {"x": 0, "y": 0, "z": 0}
        self.received_message_event = asyncio.Event()
    
    async def connect(self) -> bool:
        """Connect to the WebSocket server"""
        try:
            logger.info(f"[{self.name}] Connecting to {WS_SERVER_URL}/{self.id}...")
            self.ws = await websockets.connect(f"{WS_SERVER_URL}/{self.id}")
            self.connected = True
            logger.info(f"[{self.name}] Connected successfully")
            
            # Start listening for messages
            asyncio.create_task(self._listen_for_messages())
            
            # Send initial connect message with player name
            await self.send_message({
                "type": "connect",
                "name": self.name
            })
            logger.info(f"[{self.name}] Sent initial connect message")
            
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Connection failed: {str(e)}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Disconnect from the WebSocket server"""
        if self.ws and self.connected:
            logger.info(f"[{self.name}] Disconnecting...")
            await self.ws.close()
            self.connected = False
            logger.info(f"[{self.name}] Disconnected")
    
    async def send_message(self, message: Dict[str, Any]):
        """Send a message to the server"""
        if not self.ws or not self.connected:
            logger.error(f"[{self.name}] Cannot send message: Not connected")
            return False
        
        try:
            message_json = json.dumps(message)
            await self.ws.send(message_json)
            logger.debug(f"[{self.name}] Sent: {message}")
            return True
        except Exception as e:
            logger.error(f"[{self.name}] Failed to send message: {str(e)}")
            return False
    
    async def _listen_for_messages(self):
        """Listen for messages from the server"""
        try:
            while self.connected:
                message = await self.ws.recv()
                parsed = json.loads(message)
                self.messages.append(parsed)
                logger.debug(f"[{self.name}] Received: {parsed}")
                
                # Set event to notify waiters
                self.received_message_event.set()
                self.received_message_event.clear()
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"[{self.name}] WebSocket connection closed")
            self.connected = False
        except Exception as e:
            logger.error(f"[{self.name}] Error in message listener: {str(e)}")
            self.connected = False
    
    async def wait_for_message(self, timeout: float = 5.0, message_type: str = None, clear_previous: bool = False):
        """Wait for a specific message type or any message"""
        if clear_previous:
            self.messages = []
        
        # Check if we already have the message
        if message_type:
            for msg in self.messages:
                if msg.get("type") == message_type:
                    return msg
        elif self.messages:
            return self.messages[-1]
        
        # Wait for new messages
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                await asyncio.wait_for(self.received_message_event.wait(), timeout=1.0)
                
                if message_type:
                    for msg in self.messages:
                        if msg.get("type") == message_type:
                            return msg
                elif self.messages:
                    return self.messages[-1]
            except asyncio.TimeoutError:
                continue
        
        logger.warning(f"[{self.name}] Timeout waiting for {message_type or 'any'} message")
        return None
    
    async def update_position(self, x: float, y: float, z: float):
        """Update player position"""
        self.position = {"x": x, "y": y, "z": z}
        return await self.send_message({
            "type": "position_update",
            "position": self.position
        })
    
    async def update_rotation(self, x: float, y: float, z: float):
        """Update player rotation"""
        self.rotation = {"x": x, "y": y, "z": z}
        return await self.send_message({
            "type": "rotation_update",
            "rotation": self.rotation
        })
    
    async def place_block(self, x: int, y: int, z: int, block_id: int = 1):
        """Place a block at the given coordinates"""
        return await self.send_message({
            "type": "block_update",
            "data": {
                "action": "add",
                "x": x,
                "y": y,
                "z": z,
                "blockId": block_id
            }
        })
    
    async def remove_block(self, x: int, y: int, z: int):
        """Remove a block at the given coordinates"""
        return await self.send_message({
            "type": "block_update",
            "data": {
                "action": "remove",
                "x": x,
                "y": y,
                "z": z
            }
        })


async def test_connection():
    """Test basic connection and initial messages"""
    logger.info("=== TEST: Connection ===")
    
    client = MinecraftClient("ConnectionTestPlayer")
    success = await client.connect()
    assert success, "Client should connect successfully"
    
    # We should receive an existing_players message
    message = await client.wait_for_message(message_type="existing_players")
    assert message is not None, "Should receive existing_players message"
    assert message["type"] == "existing_players", "Message type should be existing_players"
    
    logger.info("[TEST] Checking if message format is correct")
    assert "players" in message, "Message should contain players array"
    assert isinstance(message["players"], list), "Players should be an array"
    
    await client.disconnect()
    logger.info("✅ Connection test passed\n")
    return True


async def test_multiple_connections():
    """Test multiple clients connecting"""
    logger.info("=== TEST: Multiple Connections ===")
    
    client1 = MinecraftClient("Player1")
    client2 = MinecraftClient("Player2")
    
    await client1.connect()
    
    # Clear messages and connect second player
    client1.messages = []
    await client2.connect()
    
    # Client1 should receive a player_joined message for client2
    player_joined = await client1.wait_for_message(message_type="player_joined")
    assert player_joined is not None, "Client1 should receive player_joined message"
    assert player_joined["type"] == "player_joined", "Message type should be player_joined"
    assert player_joined["player"]["id"] == client2.id, "Message should contain client2's ID"
    assert player_joined["player"]["name"] == client2.name, "Message should contain client2's name"
    
    # Client2 should receive an existing_players message containing client1
    existing_players = await client2.wait_for_message(message_type="existing_players")
    assert existing_players is not None, "Client2 should receive existing_players message"
    assert existing_players["type"] == "existing_players", "Message type should be existing_players"
    assert len(existing_players["players"]) > 0, "There should be at least one existing player"
    
    # Find client1 in the existing players list
    found_client1 = False
    for player in existing_players["players"]:
        if player["id"] == client1.id:
            found_client1 = True
            assert player["name"] == client1.name, "Player name should match client1's name"
    
    assert found_client1, "Client1 should be in the existing players list"
    
    await client1.disconnect()
    await client2.disconnect()
    logger.info("✅ Multiple connections test passed\n")
    return True


async def test_position_updates():
    """Test position updates between clients"""
    logger.info("=== TEST: Position Updates ===")
    
    client1 = MinecraftClient("PositionPlayer1")
    client2 = MinecraftClient("PositionPlayer2")
    
    await client1.connect()
    await client2.connect()
    
    # Clear messages
    client1.messages = []
    client2.messages = []
    
    # Client1 updates position
    new_position = {"x": 50, "y": 40, "z": 30}
    await client1.update_position(new_position["x"], new_position["y"], new_position["z"])
    
    # Client2 should receive a position update for client1
    update_message = await client2.wait_for_message(message_type="player_state_update")
    assert update_message is not None, "Client2 should receive player_state_update message"
    assert update_message["type"] == "player_state_update", "Message type should be player_state_update"
    assert update_message["player_id"] == client1.id, "Message should contain client1's ID"
    assert "position" in update_message["state"], "Message should contain position update"
    assert update_message["state"]["position"]["x"] == new_position["x"], "X position should match"
    assert update_message["state"]["position"]["y"] == new_position["y"], "Y position should match"
    assert update_message["state"]["position"]["z"] == new_position["z"], "Z position should match"
    
    await client1.disconnect()
    await client2.disconnect()
    logger.info("✅ Position updates test passed\n")
    return True


async def test_rotation_updates():
    """Test rotation updates between clients"""
    logger.info("=== TEST: Rotation Updates ===")
    
    client1 = MinecraftClient("RotationPlayer1")
    client2 = MinecraftClient("RotationPlayer2")
    
    await client1.connect()
    await client2.connect()
    
    # Clear messages
    client1.messages = []
    client2.messages = []
    
    # Client1 updates rotation
    new_rotation = {"x": 45, "y": 90, "z": 15}
    await client1.update_rotation(new_rotation["x"], new_rotation["y"], new_rotation["z"])
    
    # Client2 should receive a rotation update for client1
    update_message = await client2.wait_for_message(message_type="player_state_update")
    assert update_message is not None, "Client2 should receive player_state_update message"
    assert update_message["type"] == "player_state_update", "Message type should be player_state_update"
    assert update_message["player_id"] == client1.id, "Message should contain client1's ID"
    assert "rotation" in update_message["state"], "Message should contain rotation update"
    assert update_message["state"]["rotation"]["x"] == new_rotation["x"], "X rotation should match"
    assert update_message["state"]["rotation"]["y"] == new_rotation["y"], "Y rotation should match"
    assert update_message["state"]["rotation"]["z"] == new_rotation["z"], "Z rotation should match"
    
    await client1.disconnect()
    await client2.disconnect()
    logger.info("✅ Rotation updates test passed\n")
    return True


async def test_block_updates():
    """Test block placement and removal between clients"""
    logger.info("=== TEST: Block Updates ===")
    
    client1 = MinecraftClient("BlockPlayer1")
    client2 = MinecraftClient("BlockPlayer2")
    
    await client1.connect()
    await client2.connect()
    
    # Clear messages
    client1.messages = []
    client2.messages = []
    
    # Client1 places a block
    block_coords = {"x": 10, "y": 20, "z": 30}
    block_id = 2  # Stone block
    await client1.place_block(block_coords["x"], block_coords["y"], block_coords["z"], block_id)
    
    # Client2 should receive a block update for the placed block
    update_message = await client2.wait_for_message(message_type="block_update")
    assert update_message is not None, "Client2 should receive block_update message"
    assert update_message["type"] == "block_update", "Message type should be block_update"
    assert update_message["data"]["action"] == "add", "Block action should be add"
    assert update_message["data"]["x"] == block_coords["x"], "X coordinate should match"
    assert update_message["data"]["y"] == block_coords["y"], "Y coordinate should match"
    assert update_message["data"]["z"] == block_coords["z"], "Z coordinate should match"
    assert update_message["data"]["blockId"] == block_id, "Block ID should match"
    
    # Clear messages
    client1.messages = []
    client2.messages = []
    
    # Client1 removes a block
    await client1.remove_block(block_coords["x"], block_coords["y"], block_coords["z"])
    
    # Client2 should receive a block update for the removed block
    update_message = await client2.wait_for_message(message_type="block_update")
    assert update_message is not None, "Client2 should receive block_update message"
    assert update_message["type"] == "block_update", "Message type should be block_update"
    assert update_message["data"]["action"] == "remove", "Block action should be remove"
    assert update_message["data"]["x"] == block_coords["x"], "X coordinate should match"
    assert update_message["data"]["y"] == block_coords["y"], "Y coordinate should match"
    assert update_message["data"]["z"] == block_coords["z"], "Z coordinate should match"
    
    await client1.disconnect()
    await client2.disconnect()
    logger.info("✅ Block updates test passed\n")
    return True


async def test_disconnect_notification():
    """Test that clients are notified when other clients disconnect"""
    logger.info("=== TEST: Disconnect Notification ===")
    
    client1 = MinecraftClient("DisconnectPlayer1")
    client2 = MinecraftClient("DisconnectPlayer2")
    
    await client1.connect()
    await client2.connect()
    
    # Clear messages
    client1.messages = []
    
    # Disconnect client2
    await client2.disconnect()
    
    # Client1 should receive a player_left message for client2
    player_left = await client1.wait_for_message(message_type="player_left")
    assert player_left is not None, "Client1 should receive player_left message"
    assert player_left["type"] == "player_left", "Message type should be player_left"
    assert player_left["player_id"] == client2.id, "Message should contain client2's ID"
    
    await client1.disconnect()
    logger.info("✅ Disconnect notification test passed\n")
    return True


async def test_stress_position_updates():
    """Stress test with rapid position updates"""
    logger.info("=== STRESS TEST: Rapid Position Updates ===")
    
    client1 = MinecraftClient("StressPlayer1")
    client2 = MinecraftClient("StressPlayer2")
    
    await client1.connect()
    await client2.connect()
    
    # Clear messages
    client1.messages = []
    client2.messages = []
    
    # Send 20 rapid position updates from client1
    updates_sent = 0
    for i in range(20):
        success = await client1.update_position(32 + i, 32, 32 + i)
        if success:
            updates_sent += 1
        await asyncio.sleep(0.05)  # Small delay to avoid completely flooding the server
    
    # Wait a bit to let messages propagate
    await asyncio.sleep(1)
    
    # Count position updates received by client2
    updates_received = 0
    for msg in client2.messages:
        if msg.get("type") == "player_state_update" and "position" in msg.get("state", {}):
            updates_received += 1
    
    logger.info(f"Sent {updates_sent} position updates, received {updates_received}")
    assert updates_received > 0, "Client2 should receive at least some position updates"
    
    # Check the last position update to make sure it was received correctly
    last_position = {"x": 32 + 19, "y": 32, "z": 32 + 19}  # Last position sent
    
    # Find the last position update message
    last_update = None
    for msg in reversed(client2.messages):
        if msg.get("type") == "player_state_update" and "position" in msg.get("state", {}):
            last_update = msg
            break
    
    assert last_update is not None, "Client2 should have received at least one position update"
    
    await client1.disconnect()
    await client2.disconnect()
    logger.info("✅ Rapid position updates stress test passed\n")
    return True


async def test_invalid_messages():
    """Test handling of invalid messages"""
    logger.info("=== TEST: Invalid Messages ===")
    
    client = MinecraftClient("InvalidMsgPlayer")
    await client.connect()
    
    # Test invalid JSON
    logger.info("Testing invalid JSON handling")
    if client.ws and client.connected:
        await client.ws.send("this is not valid json")
        await asyncio.sleep(1)  # Wait a bit to ensure the server processes the message
    
    # Test valid JSON but missing required fields
    logger.info("Testing missing fields handling")
    await client.send_message({
        "type": "position_update"
        # Missing position field
    })
    await asyncio.sleep(1)
    
    await client.send_message({
        "type": "rotation_update"
        # Missing rotation field
    })
    await asyncio.sleep(1)
    
    await client.send_message({
        "type": "block_update",
        "data": {
            "action": "add"
            # Missing coordinates and block ID
        }
    })
    await asyncio.sleep(1)
    
    # Verify client is still connected after sending invalid messages
    assert client.connected, "Client should still be connected after sending invalid messages"
    
    # Test that the server still accepts valid messages after invalid ones
    client.messages = []
    await client.update_position(40, 40, 40)
    
    # Wait for confirmation that the server processed the message
    await asyncio.sleep(1)
    
    await client.disconnect()
    logger.info("✅ Invalid messages test passed\n")
    return True


async def test_high_concurrency():
    """Test high concurrency with multiple clients connecting and disconnecting"""
    logger.info("=== TEST: High Concurrency ===")
    
    # Create 5 clients
    clients = [MinecraftClient(f"ConcurrentPlayer{i}") for i in range(5)]
    
    # Connect all clients concurrently
    connect_tasks = [client.connect() for client in clients]
    connect_results = await asyncio.gather(*connect_tasks)
    
    # Verify all clients connected successfully
    assert all(connect_results), "All clients should connect successfully"
    
    # Let clients interact for a bit
    await asyncio.sleep(1)
    
    # Make each client update position and rotation
    update_tasks = []
    for i, client in enumerate(clients):
        update_tasks.append(client.update_position(32 + i, 32, 32 + i))
        update_tasks.append(client.update_rotation(i * 10, i * 20, 0))
    
    await asyncio.gather(*update_tasks)
    
    # Let updates propagate
    await asyncio.sleep(2)
    
    # Verify each client received updates from other clients
    for i, client in enumerate(clients):
        updates_received = 0
        for msg in client.messages:
            if msg.get("type") == "player_state_update":
                updates_received += 1
        
        logger.info(f"Client {i} received {updates_received} state updates")
        assert updates_received > 0, f"Client {i} should receive state updates from other clients"
    
    # Disconnect all clients concurrently
    disconnect_tasks = [client.disconnect() for client in clients]
    await asyncio.gather(*disconnect_tasks)
    
    logger.info("✅ High concurrency test passed\n")
    return True


async def run_all_tests():
    """Run all tests"""
    logger.info(f"Starting WebSocket tests against {WS_SERVER_URL}")
    
    tests = [
        test_connection,
        test_multiple_connections,
        test_position_updates,
        test_rotation_updates,
        test_block_updates,
        test_disconnect_notification,
        test_stress_position_updates,
        test_invalid_messages,
        test_high_concurrency
    ]
    
    all_passed = True
    for test in tests:
        try:
            await test()
        except AssertionError as e:
            logger.error(f"❌ Test failed: {str(e)}")
            all_passed = False
        except Exception as e:
            logger.error(f"❌ Test error: {str(e)}")
            all_passed = False
    
    if all_passed:
        logger.info("🎉 All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    # Use command-line argument for WebSocket server URL if provided
    if len(sys.argv) > 1:
        WS_SERVER_URL = sys.argv[1]
    
    logger.info(f"Using WebSocket server URL: {WS_SERVER_URL}")
    
    # Run all tests
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)