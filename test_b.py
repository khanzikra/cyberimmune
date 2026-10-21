"""
Test B: Nebius API tool calling test.
Sends a message with a fake tool query_events and checks if model returns a tool call.
"""
import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env
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

# Define the fake tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "query_events",
            "description": "Query security events for a user",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "User ID (e.g., user_07)",
                    },
                },
                "required": ["user_id"],
                "additionalProperties": False,
            },
        },
    }
]

try:
    client = OpenAI(api_key=api_key, base_url=base_url)
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Show me the logins for user_07."}],
        tools=tools,
        tool_choice="auto",
        max_tokens=200,
        temperature=0.1,
    )

    message = response.choices[0].message
    
    if message.tool_calls:
        for tool_call in message.tool_calls:
            print(f"Tool call: {tool_call.function.name}")
            try:
                args = json.loads(tool_call.function.arguments)
                print(f"Arguments: {json.dumps(args, indent=2)}")
            except json.JSONDecodeError as e:
                print(f"Failed to parse arguments: {e}")
                print(f"Raw arguments: {tool_call.function.arguments}")
    else:
        print("No tool call returned by the model.")
        print(f"Model response: {message.content}")

except Exception as e:
    print(f"API error: {e}")
    sys.exit(1)