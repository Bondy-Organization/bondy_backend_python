from parse_rest.connection import register

# --- Back4App Configuration ---
# Replace these placeholders with your actual keys from Back4App
# Go to App Settings > Security & Keys to find them

APPLICATION_ID = "XVHZzFd23mXRhsv9BLFUO5Vt6bGMi8LkjfBnUqhH"
REST_API_KEY = "JcAmRc006UoWNfOEzanVjyLtaAeKsURYZw1DdbWS"

# Register the keys to establish the connection
register(APPLICATION_ID, REST_API_KEY)

print("✅ Connection to Back4App initialized successfully!")