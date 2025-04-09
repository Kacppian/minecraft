import asyncio
import websockets
import json
import uuid
import pytest
import logging
import os
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get backend URL from environment or use default
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')
WS_URL = BACKEND_URL.replace('http', 'ws') + '/api/ws'

class TestMinecraftBackend:
    @pytest.mark.asyncio
    async def test_websocket_connection(self):
        """Test basic WebSocket connection and player registration"""
        player_id = str(uuid.uuid4())
        player_name = "TestPlayer"
        
        try:
            uri = f"{WS_URL}/{player_id}"
            logger.info(f"Connecting to WebSocket at {uri}")
            
            async with websockets.connect(uri) as websocket:
                # Send initial player name
                await websocket.send(json.dumps({
                    "name": player_name
                }))
                logger.info("Sent player name")
                
                # Wait for response messages
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5)
                    response_data = json.loads(response)
                    logger.info(f"Received response: {response_data}")
                    
                    assert response_data.get("type") in ["existing_players", "player_joined"], \
                        "Expected player registration confirmation"
                    
                except asyncio.TimeoutError:
                    pytest.fail("Timeout waiting for server response")
                
                # Test position update
                position_update = {
                    "type": "position_update",
                    "position": {"x": 10, "y": 20, "z": 30}
                }
                await websocket.send(json.dumps(position_update))
                logger.info("Sent position update")
                
                # Test rotation update
                rotation_update = {
                    "type": "rotation_update",
                    "rotation": {"x": 45, "y": 90, "z": 0}
                }
                await websocket.send(json.dumps(rotation_update))
                logger.info("Sent rotation update")
                
                # Test block update
                block_update = {
                    "type": "block_update",
                    "data": {
                        "action": "place",
                        "x": 5,
                        "y": 5,
                        "z": 5,
                        "block_type": "grass"
                    }
                }
                await websocket.send(json.dumps(block_update))
                logger.info("Sent block update")
                
                # Test chat message
                chat_message = {
                    "type": "chat_message",
                    "text": "Hello World!"
                }
                await websocket.send(json.dumps(chat_message))
                logger.info("Sent chat message")
                
                # Wait briefly to ensure messages are processed
                await asyncio.sleep(2)
                
            logger.info("WebSocket test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket test failed: {str(e)}")
            pytest.fail(f"WebSocket test failed: {str(e)}")
            return False

if __name__ == "__main__":
    asyncio.run(TestMinecraftBackend().test_websocket_connection())
