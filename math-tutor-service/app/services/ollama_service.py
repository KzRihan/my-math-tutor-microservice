"""
Ollama service module for LLM interactions
"""
import json
import logging
from typing import List, Dict, Optional, AsyncIterator

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


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
    self._resolved_model_name: Optional[str] = None

  def _tags_url(self) -> str:
    if self.base_url.endswith("/api/chat"):
      return f"{self.base_url[:-len('/api/chat')]}/api/tags"
    if self.base_url.endswith("/api/generate"):
      return f"{self.base_url[:-len('/api/generate')]}/api/tags"
    return f"{self.base_url.rstrip('/')}/api/tags"

  async def _safe_response_body(self, response: Optional[httpx.Response]) -> str:
    if response is None:
      return "no response body"
    try:
      await response.aread()
      return response.text
    except Exception:
      return "response body unavailable"

  async def _fetch_available_models(self) -> List[str]:
    try:
      async with httpx.AsyncClient(timeout=self.timeout) as client:
        resp = await client.get(self._tags_url())
        resp.raise_for_status()
        data = resp.json()
        models = data.get("models", [])
        return [m.get("name") for m in models if m.get("name")]
    except Exception as exc:
      logger.warning("Failed to fetch Ollama models: %s", exc)
      return []

  async def _resolve_model_name(
    self,
    requested: str,
    force_refresh: bool = False
  ) -> str:
    if not requested:
      return requested
    if not force_refresh and self._resolved_model_name == requested:
      return requested

    available = await self._fetch_available_models()
    if requested in available:
      self._resolved_model_name = requested
      return requested

    if available:
      fallback = available[0]
      logger.warning(
        "Ollama model '%s' not found. Falling back to '%s'.",
        requested,
        fallback,
      )
      self._resolved_model_name = fallback
      return fallback

    return requested

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
    requested_model = model or self.model_name
    resolved_model = await self._resolve_model_name(requested_model)
    payload = {
      "model": resolved_model,
      "messages": messages,
      "stream": stream,
    }

    async with httpx.AsyncClient(timeout=self.timeout) as client:
      try:
        resp = await client.post(self.base_url, json=payload)
        resp.raise_for_status()
      except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response else None
        body = await self._safe_response_body(exc.response)
        if status in (404, 500):
          resolved_model = await self._resolve_model_name(
            requested_model,
            force_refresh=True,
          )
          if resolved_model != payload["model"]:
            payload["model"] = resolved_model
            resp = await client.post(self.base_url, json=payload)
            resp.raise_for_status()
          else:
            raise httpx.HTTPStatusError(
              f"{exc} | Ollama response: {body}",
              request=exc.request,
              response=exc.response,
            ) from exc
        else:
          raise httpx.HTTPStatusError(
            f"{exc} | Ollama response: {body}",
            request=exc.request,
            response=exc.response,
          ) from exc
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
    requested_model = model or self.model_name
    resolved_model = await self._resolve_model_name(requested_model)
    payload = {
      "model": resolved_model,
      "messages": messages,
      "stream": True,
    }

    async with httpx.AsyncClient(timeout=self.timeout) as client:
      try:
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
      except httpx.HTTPStatusError as exc:
        status = exc.response.status_code if exc.response else None
        body = await self._safe_response_body(exc.response)
        if status in (404, 500):
          resolved_model = await self._resolve_model_name(
            requested_model,
            force_refresh=True,
          )
          if resolved_model != payload["model"]:
            payload["model"] = resolved_model
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
                  continue
          else:
            raise httpx.HTTPStatusError(
              f"{exc} | Ollama response: {body}",
              request=exc.request,
              response=exc.response,
            ) from exc
        else:
          raise httpx.HTTPStatusError(
            f"{exc} | Ollama response: {body}",
            request=exc.request,
            response=exc.response,
          ) from exc


# Create a singleton Ollama service instance
ollama_service = OllamaService()
