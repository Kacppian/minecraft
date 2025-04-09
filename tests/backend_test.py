import requests
import pytest
import websockets
import asyncio
import json
import uuid
import os

class TestMinecraftBackend:
    base_url = "https://87e4a1c9-ae10-4df8-87c0-24560c614571.preview.emergentagent.com/api"
    ws_url = "wss://87e4a1c9-ae10-4df8-87c0-24560c614571.preview.emergentagent.com/api/ws"

    def test_health_check(self):
        """Test the health check endpoint"""
        print("\n🔍 Testing Health Check API...")
        response = requests.get(f"{self.base_url}/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Hello World"
        print("✅ Health Check API test passed")

    async def test_websocket_connection(self):
        """Test basic WebSocket connection and player joining"""
        print("\n🔍 Testing WebSocket Connection...")
        player_id = str(uuid.uuid4())
        player_name = "TestPlayer"
        
        try:
            async with websockets.connect(f"{self.ws_url}/{player_id}") as websocket:
                # Send initial player info
                await websocket.send(json.dumps({
                    "type": "connect",
                    "name": player_name
                }))
                
                # Should receive existing players data
                response = await websocket.recv()
                data = json.loads(response)
                assert data["type"] == "existing_players"
                print("✅ WebSocket Connection test passed")
                self.tests_run += 1
                self.tests_passed += 1
                return True
        except Exception as e:
            print(f"❌ WebSocket Connection test failed: {str(e)}")
            self.tests_run += 1
            return False

    async def test_player_movement(self):
        """Test player position and rotation updates"""
        print("\n🔍 Testing Player Movement...")
        player_id = str(uuid.uuid4())
        
        try:
            async with websockets.connect(f"{self.ws_url}/{player_id}") as websocket:
                # Connect player
                await websocket.send(json.dumps({
                    "type": "connect",
                    "name": "MovementTestPlayer"
                }))
                
                # Skip existing players message
                await websocket.recv()
                
                # Send position update
                position = {"x": 10, "y": 20, "z": 30}
                await websocket.send(json.dumps({
                    "type": "position_update",
                    "position": position
                }))
                
                # Send rotation update
                rotation = {"x": 45, "y": 90, "z": 0}
                await websocket.send(json.dumps({
                    "type": "rotation_update",
                    "rotation": rotation
                }))
                
                print("✅ Player Movement test passed")
                self.tests_run += 1
                self.tests_passed += 1
                return True
        except Exception as e:
            print(f"❌ Player Movement test failed: {str(e)}")
            self.tests_run += 1
            return False

    async def test_block_updates(self):
        """Test block placement and removal synchronization"""
        print("\n🔍 Testing Block Updates...")
        player_id = str(uuid.uuid4())
        
        try:
            async with websockets.connect(f"{self.ws_url}/{player_id}") as websocket:
                # Connect player
                await websocket.send(json.dumps({
                    "type": "connect",
                    "name": "BlockTestPlayer"
                }))
                
                # Skip existing players message
                await websocket.recv()
                
                # Test block placement
                await websocket.send(json.dumps({
                    "type": "block_update",
                    "data": {
                        "action": "add",
                        "x": 5,
                        "y": 5,
                        "z": 5,
                        "blockId": 1
                    }
                }))
                
                # Test block removal
                await websocket.send(json.dumps({
                    "type": "block_update",
                    "data": {
                        "action": "remove",
                        "x": 5,
                        "y": 5,
                        "z": 5
                    }
                }))
                
                print("✅ Block Updates test passed")
                self.tests_run += 1
                self.tests_passed += 1
                return True
        except Exception as e:
            print(f"❌ Block Updates test failed: {str(e)}")
            self.tests_run += 1
            return False

    async def test_multiplayer_interaction(self):
        """Test interaction between multiple players"""
        print("\n🔍 Testing Multiplayer Interaction...")
        player1_id = str(uuid.uuid4())
        player2_id = str(uuid.uuid4())
        
        try:
            async with websockets.connect(f"{self.ws_url}/{player1_id}") as ws1, \
                      websockets.connect(f"{self.ws_url}/{player2_id}") as ws2:
                
                # Connect first player
                await ws1.send(json.dumps({
                    "type": "connect",
                    "name": "Player1"
                }))
                
                # Skip existing players message for player1
                await ws1.recv()
                
                # Connect second player
                await ws2.send(json.dumps({
                    "type": "connect",
                    "name": "Player2"
                }))
                
                # Player2 should receive existing players (Player1)
                response = await ws2.recv()
                data = json.loads(response)
                assert data["type"] == "existing_players"
                
                # Player1 should receive notification about Player2
                response = await ws1.recv()
                data = json.loads(response)
                assert data["type"] == "player_joined"
                assert data["player"]["name"] == "Player2"
                
                print("✅ Multiplayer Interaction test passed")
                self.tests_run += 1
                self.tests_passed += 1
                return True
        except Exception as e:
            print(f"❌ Multiplayer Interaction test failed: {str(e)}")
            self.tests_run += 1
            return False

async def run_tests():
    tester = TestMinecraftBackend()
    
    # Run HTTP test
    tester.test_health_check()
    
    # Run WebSocket tests
    await tester.test_websocket_connection()
    await tester.test_player_movement()
    await tester.test_block_updates()
    await tester.test_multiplayer_interaction()
    
    # Print test results
    print(f"\n📊 Tests Summary:")
    print(f"Total tests: {tester.tests_run}")
    print(f"Passed: {tester.tests_passed}")
    print(f"Failed: {tester.tests_run - tester.tests_passed}")
    
    return tester.tests_passed == tester.tests_run

def main():
    success = asyncio.run(run_tests())
    return 0 if success else 1

if __name__ == "__main__":
    main()