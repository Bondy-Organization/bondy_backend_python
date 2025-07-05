





import requests

url = "http://localhost:8080/register"  # Replace with your actual URL
response = requests.post(url, json={
    "username": "testuser",
    "password": "testpassword",
    "email": "asd@gmail.com"
}, timeout=10)
print(f"Status: {response.status_code}"
)

print(f"Content: {response.text}")