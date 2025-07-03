from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def hello_world():
    # This is where your script's logic would go
    return 'My Python script is running on Back4App Containers!'

if __name__ == "__main__":
    # Back4App provides the port through an environment variable
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)