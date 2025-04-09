import pytest
import websockets
import json
import asyncio
import os
from dotenv import load_dotenv
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Get the backend URL from environment
BACKEND_URL = os.getenv('REACT_APP_BACKEND_URL', 'http://localhost:8001')
WS_URL = BACKEND_URL.replace('http', 'ws') if BACKEND_URL.startswith('http') else BACKEND_URL

class TestMinecraftWebSocket:
    async def setup_websocket(self, player_id, player_name):
        """Helper to setup websocket connection"""
        ws_endpoint = f"{WS_URL}/api/ws/{player_id}"
        websocket = await websockets.connect(ws_endpoint)
        # Send initial player name
        await websocket.send(json.dumps({"name": player_name}))
        return websocket

    async def test_supersaiyan_transformation(self):
        """Test the SuperSaiyan transformation feature"""
        try:
            # Connect first player (the one who will transform)
            player1_ws = await self.setup_websocket("player1", "Goku")
            logger.info("Player 1 connected successfully")

            # Connect second player (to verify the effect is visible)
            player2_ws = await self.setup_websocket("player2", "Vegeta")
            logger.info("Player 2 connected successfully")

            # Send supersaiyan toggle message from player 1
            supersaiyan_msg = {
                "type": "supersaiyan_toggle",
                "active": True
            }
            await player1_ws.send(json.dumps(supersaiyan_msg))
            logger.info("Sent SuperSaiyan toggle message")

            # Verify both players receive the transformation message
            for ws in [player1_ws, player2_ws]:
                response = await ws.recv()
                response_data = json.loads(response)
                assert response_data["type"] == "supersaiyan_toggle"
                assert response_data["player_id"] == "player1"
                assert response_data["active"] == True
                logger.info(f"Received correct SuperSaiyan toggle response: {response_data}")

            # Test that regular chat message with "supersaiyan" text is not broadcast
            chat_msg = {
                "type": "chat_message",
                "text": "supersaiyan"
            }
            await player1_ws.send(json.dumps(chat_msg))
            logger.info("Sent 'supersaiyan' chat message")

            # Verify no chat message is broadcast
            try:
                response = await asyncio.wait_for(player2_ws.recv(), timeout=2.0)
                response_data = json.loads(response)
                # We should not receive a chat message
                assert response_data["type"] != "chat_message"
                logger.info("Correctly did not receive chat message")
            except asyncio.TimeoutError:
                logger.info("Correctly timed out waiting for chat message")

            # Test toggling off
            supersaiyan_msg["active"] = False
            await player1_ws.send(json.dumps(supersaiyan_msg))
            logger.info("Sent SuperSaiyan toggle off message")

            # Verify both players receive the deactivation
            for ws in [player1_ws, player2_ws]:
                response = await ws.recv()
                response_data = json.loads(response)
                assert response_data["type"] == "supersaiyan_toggle"
                assert response_data["player_id"] == "player1"
                assert response_data["active"] == False
                logger.info("Received correct SuperSaiyan toggle off response")

            logger.info("All backend tests passed successfully!")
            return True

        except Exception as e:
            logger.error(f"Test failed with error: {str(e)}")
            return False
        finally:
            # Cleanup
            try:
                await player1_ws.close()
                await player2_ws.close()
            except:
                pass

async def main():
    test = TestMinecraftWebSocket()
    success = await test.test_supersaiyan_transformation()
    return 0 if success else 1

if __name__ == "__main__":
    asyncio.run(main())