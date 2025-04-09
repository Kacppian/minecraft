#!/usr/bin/env python3
import asyncio
import json
import logging
import uuid
import pytest
import websockets
import sys
import time
from typing import Dict, List, Tuple, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebSocketTester")

# Get WebSocket URL from environment or use default for testing locally
# Make sure to use the correct URL for your deployment
WS_URL = "ws://localhost:8000/ws"  # Default WebSocket URL

class WebSocketClient:
    """Class to simulate a Minecraft client connected via WebSocket"""
    
    def __init__(self, player_id: str, player_name: str):
        self.player_id = player_id
        self.player_name = player_name
        self.websocket = None
        self.message_queue = asyncio.Queue()
        self.connected = False
        self.position = {"x": 32, "y": 32, "z": 32}
        self.rotation = {"x": 0, "y": 0, "z": 0}
        
    async def connect(self) -> None:
        """Connect to the WebSocket server"""
        try:
            logger.info(f"Connecting client {self.player_name} ({self.player_id})...")
            self.websocket = await websockets.connect(f"{WS_URL}/{self.player_id}")
            self.connected = True
            
            # Send initial connect message with player name
            await self.send_message({
                "type": "connect",
                "name": self.player_name
            })
            
            # Start the message receiver task
            asyncio.create_task(self.receive_messages())
            logger.info(f"Client {self.player_name} connected successfully")
            return True
        except Exception as e:
            logger.error(f"Connection failed for {self.player_name}: {str(e)}")
            self.connected = False
            return False
    
    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server"""
        if self.websocket and self.connected:
            await self.websocket.close()
            self.connected = False
            logger.info(f"Client {self.player_name} disconnected")
    
    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message to the WebSocket server"""
        if not self.websocket or not self.connected:
            logger.error(f"Cannot send message: {self.player_name} not connected")
            return
        
        try:
            await self.websocket.send(json.dumps(message))
            logger.debug(f"Sent message from {self.player_name}: {message}")
        except Exception as e:
            logger.error(f"Error sending message from {self.player_name}: {str(e)}")
    
    async def receive_messages(self) -> None:
        """Continuously receive messages and store them in the queue"""
        if not self.websocket or not self.connected:
            return
        
        try:
            while self.connected:
                message = await self.websocket.recv()
                parsed_message = json.loads(message)
                logger.debug(f"Received message for {self.player_name}: {parsed_message}")
                await self.message_queue.put(parsed_message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"WebSocket connection closed for {self.player_name}")
            self.connected = False
        except Exception as e:
            logger.error(f"Error receiving messages for {self.player_name}: {str(e)}")
            self.connected = False
    
    async def get_next_message(self, timeout: float = 5.0) -> Dict[str, Any]:
        """Get the next message from the queue with a timeout"""
        try:
            return await asyncio.wait_for(self.message_queue.get(), timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for message for {self.player_name}")
            return None
    
    async def update_position(self, x: float, y: float, z: float) -> None:
        """Update player position and send to server"""
        self.position = {"x": x, "y": y, "z": z}
        await self.send_message({
            "type": "position_update",
            "position": self.position
        })
    
    async def update_rotation(self, x: float, y: float, z: float) -> None:
        """Update player rotation and send to server"""
        self.rotation = {"x": x, "y": y, "z": z}
        await self.send_message({
            "type": "rotation_update",
            "rotation": self.rotation
        })
    
    async def place_block(self, x: int, y: int, z: int, block_id: int) -> None:
        """Place a block at the given coordinates"""
        await self.send_message({
            "type": "block_update",
            "data": {
                "action": "add",
                "x": x,
                "y": y,
                "z": z,
                "blockId": block_id
            }
        })
    
    async def remove_block(self, x: int, y: int, z: int) -> None:
        """Remove a block at the given coordinates"""
        await self.send_message({
            "type": "block_update",
            "data": {
                "action": "remove",
                "x": x,
                "y": y,
                "z": z
            }
        })


class TestMultiplayer:
    """Test class for Minecraft multiplayer functionality"""
    
    @classmethod
    def setup_class(cls):
        """Set up test fixtures before running tests"""
        logger.info("Setting up test fixtures")
    
    @classmethod
    def teardown_class(cls):
        """Tear down test fixtures after running tests"""
        logger.info("Tearing down test fixtures")
    
    @pytest.fixture(scope="function")
    async def client(self):
        """Create and connect a test client"""
        player_id = str(uuid.uuid4())
        player_name = f"TestPlayer-{player_id[:5]}"
        client = WebSocketClient(player_id, player_name)
        
        connection_success = await client.connect()
        if not connection_success:
            pytest.skip("Failed to connect test client to WebSocket server")
        
        yield client
        
        await client.disconnect()
    
    @pytest.fixture(scope="function")
    async def two_clients(self):
        """Create and connect two test clients"""
        player1_id = str(uuid.uuid4())
        player1_name = f"Player1-{player1_id[:5]}"
        client1 = WebSocketClient(player1_id, player1_name)
        
        player2_id = str(uuid.uuid4())
        player2_name = f"Player2-{player2_id[:5]}"
        client2 = WebSocketClient(player2_id, player2_name)
        
        # Connect both clients
        c1_success = await client1.connect()
        c2_success = await client2.connect()
        
        if not c1_success or not c2_success:
            pytest.skip("Failed to connect test clients to WebSocket server")
        
        # Wait a bit to allow initial messages to be processed
        await asyncio.sleep(1)
        
        yield (client1, client2)
        
        # Disconnect both clients
        await client1.disconnect()
        await client2.disconnect()
    
    @pytest.mark.asyncio
    async def test_connection(self, client):
        """Test that a client can connect to the WebSocket server"""
        logger.info("Running test_connection")
        assert client.connected, "Client should be connected"
        
        # First message should be 'existing_players'
        message = await client.get_next_message()
        assert message is not None, "Should receive a message after connecting"
        assert message.get("type") == "existing_players", f"First message should be 'existing_players', got {message.get('type')}"
        
        logger.info("test_connection passed")
    
    @pytest.mark.asyncio
    async def test_player_join_notification(self, two_clients):
        """Test that players are notified when other players join"""
        logger.info("Running test_player_join_notification")
        client1, client2 = two_clients
        
        # Player1 should have received a notification about Player2 joining
        # This may be in the message queue already, so we'll check for it
        join_notification = None
        
        # Try to find the player_joined message in the queue
        found = False
        for _ in range(5):  # Check up to 5 messages
            if client1.message_queue.empty():
                break
                
            message = await client1.get_next_message(1)
            if message and message.get("type") == "player_joined":
                join_notification = message
                found = True
                break
        
        if not found:
            # If not found, wait for a new message
            join_notification = await client1.get_next_message()
        
        assert join_notification is not None, "Player1 should receive notification when Player2 joins"
        assert join_notification.get("type") == "player_joined", f"Notification should be of type 'player_joined', got {join_notification.get('type')}"
        assert join_notification.get("player").get("id") == client2.player_id, "Notification should contain Player2's ID"
        assert join_notification.get("player").get("name") == client2.player_name, "Notification should contain Player2's name"
        
        logger.info("test_player_join_notification passed")
    
    @pytest.mark.asyncio
    async def test_position_updates(self, two_clients):
        """Test that position updates are synchronized between players"""
        logger.info("Running test_position_updates")
        client1, client2 = two_clients
        
        # Clear message queues
        while not client1.message_queue.empty():
            await client1.message_queue.get()
        while not client2.message_queue.empty():
            await client2.message_queue.get()
        
        # Player1 updates position
        new_position = {"x": 50, "y": 40, "z": 60}
        await client1.update_position(new_position["x"], new_position["y"], new_position["z"])
        
        # Player2 should receive the position update
        update_message = await client2.get_next_message()
        assert update_message is not None, "Player2 should receive position update from Player1"
        assert update_message.get("type") == "player_state_update", f"Update message should be of type 'player_state_update', got {update_message.get('type')}"
        assert update_message.get("player_id") == client1.player_id, "Update message should contain Player1's ID"
        assert update_message.get("state").get("position") == new_position, f"Update message should contain the new position {new_position}, got {update_message.get('state').get('position')}"
        
        logger.info("test_position_updates passed")
    
    @pytest.mark.asyncio
    async def test_rotation_updates(self, two_clients):
        """Test that rotation updates are synchronized between players"""
        logger.info("Running test_rotation_updates")
        client1, client2 = two_clients
        
        # Clear message queues
        while not client1.message_queue.empty():
            await client1.message_queue.get()
        while not client2.message_queue.empty():
            await client2.message_queue.get()
        
        # Player1 updates rotation
        new_rotation = {"x": 45, "y": 90, "z": 0}
        await client1.update_rotation(new_rotation["x"], new_rotation["y"], new_rotation["z"])
        
        # Player2 should receive the rotation update
        update_message = await client2.get_next_message()
        assert update_message is not None, "Player2 should receive rotation update from Player1"
        assert update_message.get("type") == "player_state_update", f"Update message should be of type 'player_state_update', got {update_message.get('type')}"
        assert update_message.get("player_id") == client1.player_id, "Update message should contain Player1's ID"
        assert update_message.get("state").get("rotation") == new_rotation, f"Update message should contain the new rotation {new_rotation}, got {update_message.get('state').get('rotation')}"
        
        logger.info("test_rotation_updates passed")
    
    @pytest.mark.asyncio
    async def test_block_placement(self, two_clients):
        """Test that block placement is synchronized between players"""
        logger.info("Running test_block_placement")
        client1, client2 = two_clients
        
        # Clear message queues
        while not client1.message_queue.empty():
            await client1.message_queue.get()
        while not client2.message_queue.empty():
            await client2.message_queue.get()
        
        # Player1 places a block
        block_x, block_y, block_z = 10, 20, 30
        block_id = 1  # Dirt block
        await client1.place_block(block_x, block_y, block_z, block_id)
        
        # Player2 should receive the block update
        update_message = await client2.get_next_message()
        assert update_message is not None, "Player2 should receive block placement update from Player1"
        assert update_message.get("type") == "block_update", f"Update message should be of type 'block_update', got {update_message.get('type')}"
        
        block_data = update_message.get("data", {})
        assert block_data.get("action") == "add", f"Block action should be 'add', got {block_data.get('action')}"
        assert block_data.get("x") == block_x, f"Block X coordinate should be {block_x}, got {block_data.get('x')}"
        assert block_data.get("y") == block_y, f"Block Y coordinate should be {block_y}, got {block_data.get('y')}"
        assert block_data.get("z") == block_z, f"Block Z coordinate should be {block_z}, got {block_data.get('z')}"
        assert block_data.get("blockId") == block_id, f"Block ID should be {block_id}, got {block_data.get('blockId')}"
        
        logger.info("test_block_placement passed")
    
    @pytest.mark.asyncio
    async def test_block_removal(self, two_clients):
        """Test that block removal is synchronized between players"""
        logger.info("Running test_block_removal")
        client1, client2 = two_clients
        
        # Clear message queues
        while not client1.message_queue.empty():
            await client1.message_queue.get()
        while not client2.message_queue.empty():
            await client2.message_queue.get()
        
        # Player1 removes a block
        block_x, block_y, block_z = 15, 25, 35
        await client1.remove_block(block_x, block_y, block_z)
        
        # Player2 should receive the block update
        update_message = await client2.get_next_message()
        assert update_message is not None, "Player2 should receive block removal update from Player1"
        assert update_message.get("type") == "block_update", f"Update message should be of type 'block_update', got {update_message.get('type')}"
        
        block_data = update_message.get("data", {})
        assert block_data.get("action") == "remove", f"Block action should be 'remove', got {block_data.get('action')}"
        assert block_data.get("x") == block_x, f"Block X coordinate should be {block_x}, got {block_data.get('x')}"
        assert block_data.get("y") == block_y, f"Block Y coordinate should be {block_y}, got {block_data.get('y')}"
        assert block_data.get("z") == block_z, f"Block Z coordinate should be {block_z}, got {block_data.get('z')}"
        
        logger.info("test_block_removal passed")
    
    @pytest.mark.asyncio
    async def test_player_disconnect(self, two_clients):
        """Test that players are notified when other players disconnect"""
        logger.info("Running test_player_disconnect")
        client1, client2 = two_clients
        
        # Clear message queues
        while not client1.message_queue.empty():
            await client1.message_queue.get()
        while not client2.message_queue.empty():
            await client2.message_queue.get()
        
        # Disconnect Player2
        await client2.disconnect()
        
        # Player1 should receive a notification about Player2 leaving
        leave_notification = await client1.get_next_message()
        assert leave_notification is not None, "Player1 should receive notification when Player2 leaves"
        assert leave_notification.get("type") == "player_left", f"Notification should be of type 'player_left', got {leave_notification.get('type')}"
        assert leave_notification.get("player_id") == client2.player_id, "Notification should contain Player2's ID"
        
        logger.info("test_player_disconnect passed")
    
    @pytest.mark.asyncio
    async def test_rapid_position_updates(self, two_clients):
        """Test rapid position updates to simulate player movement"""
        logger.info("Running test_rapid_position_updates")
        client1, client2 = two_clients
        
        # Clear message queues
        while not client1.message_queue.empty():
            await client1.message_queue.get()
        while not client2.message_queue.empty():
            await client2.message_queue.get()
        
        # Send 10 position updates in quick succession
        updates_sent = 0
        for i in range(10):
            x = 32 + i
            y = 32
            z = 32 + i
            await client1.update_position(x, y, z)
            updates_sent += 1
            await asyncio.sleep(0.1)  # Small delay to avoid flooding
        
        # Player2 should receive at least some of the updates
        # We don't expect to receive all of them due to throttling on the server side
        updates_received = 0
        deadline = time.time() + 5  # 5 second timeout
        
        while time.time() < deadline and updates_received < updates_sent:
            update_message = await client2.get_next_message(1)
            if update_message and update_message.get("type") == "player_state_update":
                updates_received += 1
        
        logger.info(f"Sent {updates_sent} position updates, received {updates_received}")
        assert updates_received > 0, "Player2 should receive at least one position update"
        
        logger.info("test_rapid_position_updates passed")

if __name__ == "__main__":
    logger.info("Starting WebSocket tester")
    
    if len(sys.argv) > 1:
        WS_URL = sys.argv[1]
    
    logger.info(f"Using WebSocket URL: {WS_URL}")
    # Use pytest to run the tests
    sys.exit(pytest.main(["-xvs", __file__]))