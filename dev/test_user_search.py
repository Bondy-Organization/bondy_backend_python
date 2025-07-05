
import requests

BASE_URL = "http://localhost:8082"

response = requests.get(f"{BASE_URL}/users?username=a", timeout=10)
print(f"Status: {response.status_code}")
print(f"Content: {response.text}")