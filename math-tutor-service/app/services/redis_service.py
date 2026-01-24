"""
Redis service module for session management
"""
import json
from typing import List, Dict, Optional

import redis

from app.core.config import settings


class RedisService:
  """Redis service for session management"""

  def __init__(
    self,
    host: Optional[str] = None,
    port: Optional[int] = None,
    db: Optional[int] = None,
    password: Optional[str] = None,
    decode_responses: Optional[bool] = None
  ):
    """
    Initialize Redis service with dynamic configuration

    Args:
      host: Redis host (defaults to settings.REDIS_HOST)
      port: Redis port (defaults to settings.REDIS_PORT)
      db: Redis database number (defaults to settings.REDIS_DB)
      password: Redis password (defaults to settings.REDIS_PASSWORD)
      decode_responses: Whether to decode responses
        (defaults to settings.REDIS_DECODE_RESPONSES)
    """
    self.host = host or settings.REDIS_HOST
    self.port = port or settings.REDIS_PORT
    self.db = db or settings.REDIS_DB
    self.password = password or settings.REDIS_PASSWORD
    self.decode_responses = (
      decode_responses
      if decode_responses is not None
      else settings.REDIS_DECODE_RESPONSES
    )
    self.session_ttl = settings.REDIS_SESSION_TTL

    self._client: Optional[redis.Redis] = None

  @property
  def client(self) -> redis.Redis:
    """Lazy initialization of Redis client"""
    if self._client is None:
      self._client = redis.Redis(
        host=self.host,
        port=self.port,
        db=self.db,
        password=self.password,
        decode_responses=self.decode_responses,
      )
    return self._client

  def load_history(self, session_id: str) -> List[Dict[str, str]]:
    """
    Load conversation history for a session

    Args:
      session_id: Unique session identifier

    Returns:
      List of message dictionaries with 'role' and 'content' keys
    """
    try:
      data = self.client.get(session_id)
      return json.loads(data) if data else []
    except (json.JSONDecodeError, redis.RedisError) as e:
      # Log error in production, return empty history for now
      return []

  def save_history(
    self, session_id: str, messages: List[Dict[str, str]]
  ) -> bool:
    """
    Save conversation history for a session

    Args:
      session_id: Unique session identifier
      messages: List of message dictionaries with 'role' and
        'content' keys

    Returns:
      True if successful, False otherwise
    """
    try:
      self.client.set(
        session_id,
        json.dumps(messages),
        ex=self.session_ttl,
      )
      return True
    except (redis.RedisError, TypeError) as e:
      # Log error in production
      return False

  def delete_session(self, session_id: str) -> bool:
    """
    Delete a session from Redis

    Args:
      session_id: Unique session identifier

    Returns:
      True if successful, False otherwise
    """
    try:
      return bool(self.client.delete(session_id))
    except redis.RedisError:
      return False

  def ping(self) -> bool:
    """
    Check Redis connection

    Returns:
      True if connected, False otherwise
    """
    try:
      return self.client.ping()
    except redis.RedisError:
      return False


# Create a singleton Redis service instance
redis_service = RedisService()
