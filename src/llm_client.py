"""
LLM client for Nebius Token Factory / NVIDIA API.
The ONLY file that talks to the API.
"""
import os
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from openai.types.chat import ChatCompletionMessageParam

from dotenv import load_dotenv

load_dotenv()


def get_client() -> OpenAI:
    """Build OpenAI client from environment variables."""
    api_key = os.getenv("NVIDIA_API_KEY")
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    model = os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

    if not api_key:
        raise ValueError("NVIDIA_API_KEY not set in environment")

    return OpenAI(api_key=api_key, base_url=base_url)


def chat(
    messages: List[ChatCompletionMessageParam],
    tools: Optional[List[Dict[str, Any]]] = None,
    temperature: float = 0.0,
    model: Optional[str] = None,
    max_retries: int = 2,
    timeout: float = 120.0,
) -> Any:
    """
    Call the chat completion API with retries on transient errors.
    Returns the raw response object.
    """
    client = get_client()
    model_name = model or os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-ultra-550b-a55b")

    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto" if tools else None,
                temperature=temperature,
                max_tokens=4000,
                timeout=timeout,
            )
            return response
        except Exception as e:
            last_error = e
            # Retry on transient errors
            if attempt < max_retries:
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ["timeout", "500", "502", "503", "504", "rate limit", "connection"]):
                    time.sleep(1.5 * (attempt + 1))
                    continue
            # Non-retryable or max retries reached
            raise

    # Should not reach here
    raise last_error


def extract_message(response: Any) -> Dict[str, Any]:
    """Extract standardized message info from response."""
    msg = response.choices[0].message
    result = {
        "role": "assistant",
        "content": msg.content,
        "tool_calls": None,
    }
    if msg.tool_calls:
        result["tool_calls"] = [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return result


if __name__ == "__main__":
    # Quick test
    resp = chat([{"role": "user", "content": "Say hello in one short sentence."}])
    print(extract_message(resp))