"""
Ollama service module for LLM interactions
"""
import json
from typing import List, Dict, Optional, AsyncIterator

import httpx

from app.core.config import settings


class OllamaService:
  """Service for interacting with Ollama API"""

  def __init__(
    self,
    base_url: Optional[str] = None,
    model_name: Optional[str] = None,
    timeout: Optional[float] = None
  ):
    """
    Initialize Ollama service with dynamic configuration

    Args:
      base_url: Ollama API base URL
        (defaults to settings.OLLAMA_CHAT_URL)
      model_name: Model name to use
        (defaults to settings.MODEL_NAME)
      timeout: Request timeout in seconds (None for no timeout)
    """
    self.base_url = base_url or settings.OLLAMA_CHAT_URL
    self.model_name = model_name or settings.MODEL_NAME
    self.timeout = timeout

  async def call(
    self,
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    stream: bool = False
  ) -> str:
    """
    Make a non-streaming call to Ollama API

    Args:
      messages: List of message dictionaries with 'role' and
        'content' keys
      model: Model name to use (defaults to instance model_name)
      stream: Whether to stream (should be False for this method)

    Returns:
      Response content as string

    Raises:
      httpx.HTTPStatusError: If the API request fails
    """
    payload = {
      "model": model or self.model_name,
      "messages": messages,
      "stream": stream,
    }

    async with httpx.AsyncClient(timeout=self.timeout) as client:
      resp = await client.post(self.base_url, json=payload)
      resp.raise_for_status()
      return resp.json()["message"]["content"]

  async def stream(
    self,
    messages: List[Dict[str, str]],
    model: Optional[str] = None
  ) -> AsyncIterator[str]:
    """
    Stream responses from Ollama API

    Args:
      messages: List of message dictionaries with 'role' and
        'content' keys
      model: Model name to use (defaults to instance model_name)

    Yields:
      Response content tokens as strings

    Raises:
      httpx.HTTPStatusError: If the API request fails
    """
    payload = {
      "model": model or self.model_name,
      "messages": messages,
      "stream": True,
    }

    async with httpx.AsyncClient(timeout=self.timeout) as client:
      async with client.stream(
        "POST",
        self.base_url,
        json=payload,
      ) as resp:
        resp.raise_for_status()
        async for line in resp.aiter_lines():
          if not line:
            continue
          try:
            data = json.loads(line)
            if "message" in data and "content" in data["message"]:
              yield data["message"]["content"]
          except json.JSONDecodeError:
            # Skip malformed JSON lines
            continue


# Create a singleton Ollama service instance
ollama_service = OllamaService()
