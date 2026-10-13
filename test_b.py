"""
Test B: Tool calling test with a fake query_events tool.
Checks if the model returns a tool call for query_events with user_07.
"""
import os
import sys
import json
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

tools = [
    {
        "type": "function",
        "function": {
            "name": "query_events",
            "description": "Look up security events for a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "string", "description": "User ID like user_07"}
                },
                "required": ["user_id"],
                "additionalProperties": False,
            },
        },
    }
]

try:
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Show me the logins for user_07."}],
        tools=tools,
        tool_choice="auto",
        temperature=0.0,
        max_tokens=200,
    )
    msg = resp.choices[0].message
    if msg.tool_calls:
        for tc in msg.tool_calls:
            if tc.function.name == "query_events":
                try:
                    args = json.loads(tc.function.arguments)
                    print(f"Tool call: {tc.function.name}")
                    print(f"Arguments: {json.dumps(args, indent=2)}")
                except json.JSONDecodeError:
                    print(f"Tool call: {tc.function.name}")
                    print(f"Arguments (raw, invalid JSON): {tc.function.arguments}")
                break
        else:
            print("Model returned tool call(s), but not query_events")
    else:
        print("No tool call returned by the model.")
        print(f"Model reply: {msg.content}")
except Exception as e:
    print(f"API error: {e}")
    sys.exit(1)