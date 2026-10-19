"""
Test A: Basic Nebius API connection test.
Loads .env, builds OpenAI client, sends one chat message.
"""
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env (not .env.example)
load_dotenv()

# Required environment variables
required_vars = ["NEBIUS_API_KEY", "NEBIUS_BASE_URL", "NEBIUS_MODEL"]
missing = [var for var in required_vars if not os.getenv(var)]

if missing:
    print(f"Missing environment variables: {', '.join(missing)}")
    print("Please set them in a .env file (see .env.example)")
    sys.exit(1)

api_key = os.getenv("NEBIUS_API_KEY")
base_url = os.getenv("NEBIUS_BASE_URL")
model = os.getenv("NEBIUS_MODEL")

print(f"Using model: {model}")
print(f"Base URL: {base_url}")

try:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello in one short sentence."}],
        max_tokens=50,
        temperature=0.1,
    )
    print(response.choices[0].message.content)
except Exception as e:
    print(f"API error: {e}")
    sys.exit(1)