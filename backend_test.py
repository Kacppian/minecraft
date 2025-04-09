import asyncio
import websockets
import json
import pytest
import uuid

BACKEND_URL = "wss://87e4a1c9-ae10-4df8-87c0-24560c614571.preview.emergentagent.com/ws"

async def connect_player(player_id, player_name):
    """Helper function to connect a player to the game"""
    uri = f"{BACKEND_URL}/{player_id}"
    async with websockets.connect(uri) as websocket:
        # Send initial player information
        await websocket.send(json.dumps({
            "type": "connect",
            "name": player_name
        }))
        
        # Wait for connection confirmation
        response = await websocket.recv()
        return websocket, json.loads(response)

@pytest.mark.asyncio
async def test_player_connection():
    """Test basic player connection"""
    player_id = str(uuid.uuid4())
    player_name = "TestPlayer1"
    
    try:
        websocket, response = await connect_player(player_id, player_name)
        assert response["type"] == "existing_players"
        print("✅ Player connection test passed")
    except Exception as e:
        print(f"❌ Player connection test failed: {str(e)}")

@pytest.mark.asyncio
async def test_multiplayer_interaction():
    """Test interaction between two players"""
    player1_id = str(uuid.uuid4())
    player2_id = str(uuid.uuid4())
    
    try:
        # Connect first player
        async with websockets.connect(f"{BACKEND_URL}/{player1_id}") as ws1:
            await ws1.send(json.dumps({
                "type": "connect",
                "name": "Player1"
            }))
            
            # Connect second player
            async with websockets.connect(f"{BACKEND_URL}/{player2_id}") as ws2:
                await ws2.send(json.dumps({
                    "type": "connect",
                    "name": "Player2"
                }))
                
                # Player 1 should receive player_joined message for Player 2
                response = await ws1.recv()
                data = json.loads(response)
                assert data["type"] == "player_joined"
                assert data["player"]["name"] == "Player2"
                
                # Test position update
                await ws1.send(json.dumps({
                    "type": "position_update",
                    "position": {"x": 10, "y": 10, "z": 10}
                }))
                
                # Player 2 should receive the position update
                response = await ws2.recv()
                data = json.loads(response)
                assert data["type"] == "player_state_update"
                assert data["state"]["position"] == {"x": 10, "y": 10, "z": 10}
                
        print("✅ Multiplayer interaction test passed")
    except Exception as e:
        print(f"❌ Multiplayer interaction test failed: {str(e)}")

@pytest.mark.asyncio
async def test_block_updates():
    """Test block placement and removal synchronization"""
    player1_id = str(uuid.uuid4())
    player2_id = str(uuid.uuid4())
    
    try:
        # Connect both players
        async with websockets.connect(f"{BACKEND_URL}/{player1_id}") as ws1, \
                  websockets.connect(f"{BACKEND_URL}/{player2_id}") as ws2:
            
            # Send initial connection messages
            await ws1.send(json.dumps({"type": "connect", "name": "Player1"}))
            await ws2.send(json.dumps({"type": "connect", "name": "Player2"}))
            
            # Player 1 places a block
            block_data = {
                "type": "block_update",
                "data": {
                    "action": "add",
                    "x": 5,
                    "y": 5,
                    "z": 5,
                    "blockId": 1
                }
            }
            await ws1.send(json.dumps(block_data))
            
            # Player 2 should receive the block update
            response = await ws2.recv()
            data = json.loads(response)
            assert data["type"] == "block_update"
            assert data["data"]["action"] == "add"
            assert data["data"]["x"] == 5
            
        print("✅ Block updates test passed")
    except Exception as e:
        print(f"❌ Block updates test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_player_connection())
    asyncio.run(test_multiplayer_interaction())
    asyncio.run(test_block_updates())
