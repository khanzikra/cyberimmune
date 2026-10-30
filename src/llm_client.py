"""
LLM client - the ONLY file that talks to Nebius/NVIDIA API.
"""
import os
import time
from typing import List, Dict, Any, Optional

from openai import OpenAI
from dotenv import load_dotenv

# Load .env once
load_dotenv()


class LLMClient:
    """Wrapper for Nebius/NVIDIA OpenAI-compatible API."""

    def __init__(self):
        self.api_key = os.getenv("NEBIUS_API_KEY")
        self.base_url = os.getenv("NEBIUS_BASE_URL")
        self.model = os.getenv("NEBIUS_MODEL")

        if not all([self.api_key, self.base_url, self.model]):
            raise ValueError("Missing required env vars: NEBIUS_API_KEY, NEBIUS_BASE_URL, NEBIUS_MODEL")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=60.0,
            max_retries=0,  # We handle retries manually
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> Dict[str, Any]:
        """
        Send a chat completion request with up to 2 retries on transient errors.
        Returns the parsed message dict (not the full response).
        """
        last_error = None

        for attempt in range(3):  # Initial + 2 retries
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto" if tools else None,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

                message = response.choices[0].message

                # Build result dict - handle content being None
                result = {
                    "role": message.role,
                    "content": message.content,
                }

                if message.tool_calls:
                    result["tool_calls"] = [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in message.tool_calls
                    ]
                # Ignore any extra reasoning fields
                return result

            except Exception as e:
                last_error = e
                error_str = str(e).lower()

                # Check if it's a transient error worth retrying
                transient = any(x in error_str for x in [
                    "timeout", "connection", "502", "503", "504", "rate limit",
                    "temporary", "unavailable", "econnreset", "etimedout"
                ])

                if transient and attempt < 2:
                    time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
                    continue

                # Non-transient or max retries reached
                raise RuntimeError(f"LLM API error after {attempt + 1} attempt(s): {last_error}")

        # Should not reach here
        raise RuntimeError(f"LLM API error: {last_error}")


def chat(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    temperature: float = 0.0,
    model: Optional[str] = None,
    max_retries: int = 2,
    timeout: float = 120.0,
) -> Any:
    """
    Call the chat completion API with retries.
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
            if attempt < max_retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise

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


def get_client() -> LLMClient:
    """Get or create the LLM client."""
    return LLMClient()