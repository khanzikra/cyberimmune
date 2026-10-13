"""
Test A: Basic chat completion with NVIDIA API.
Loads .env, builds OpenAI client, sends one message, prints reply.
"""
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("NVIDIA_API_KEY")
base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra")

missing = []
if not api_key:
    missing.append("NVIDIA_API_KEY")

if missing:
    print(f"Missing environment variables: {', '.join(missing)}")
    print("Add them to .env file (see .env.example)")
    sys.exit(0)

client = OpenAI(api_key=api_key, base_url=base_url)

try:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Say hello in one short sentence."}],
        temperature=0.0,
        max_tokens=50,
    )
    print(resp.choices[0].message.content)
except Exception as e:
    print(f"API error: {e}")
    sys.exit(1)