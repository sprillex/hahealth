import json
import os
import sys

# Ensure the app module can be imported
sys.path.append(os.getcwd())

from app.main import app

def generate_openapi_json():
    print("Generating openapi.json...")
    openapi_data = app.openapi()

    with open("openapi.json", "w") as f:
        json.dump(openapi_data, f, indent=2)

    print("openapi.json generated successfully.")

if __name__ == "__main__":
    generate_openapi_json()
