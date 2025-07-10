





import requests

url = "https://bondy-backend-python-mi3a.onrender.com/register"  # Replace with your actual URL
response = requests.post(url, json={
    "username": "asdedwqdodmqw",
    "password": "testpassword",
    "email": "asdedwqdodmqw@gmail.com"
}, timeout=10)
print(f"Status: {response.status_code}"
)

print(f"Content: {response.text}")