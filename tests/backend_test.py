import requests
import pytest

class TestMinecraftBackend:
    def __init__(self):
        self.base_url = "https://87e4a1c9-ae10-4df8-87c0-24560c614571.preview.emergentagent.com/api"
        self.tests_run = 0
        self.tests_passed = 0

    def test_health_check(self):
        """Test the health check endpoint"""
        print("\n🔍 Testing Health Check API...")
        try:
            response = requests.get(f"{self.base_url}/")
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Hello World"
            print("✅ Health Check API test passed")
            return True
        except Exception as e:
            print(f"❌ Health Check API test failed: {str(e)}")
            return False

def main():
    tester = TestMinecraftBackend()
    success = tester.test_health_check()
    return 0 if success else 1

if __name__ == "__main__":
    main()