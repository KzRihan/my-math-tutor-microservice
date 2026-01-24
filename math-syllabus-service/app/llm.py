import httpx
import logging
import asyncio
from app.config import OLLAMA_BASE_URL, MODEL_NAME

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0  # seconds


async def generate_text(prompt: str, max_retries: int = MAX_RETRIES) -> str:
    """
    Generate text using Ollama LLM with retry logic.

    Args:
      prompt: The prompt to send to the LLM
      max_retries: Maximum number of retry attempts

    Returns:
      The generated text response

    Raises:
      httpx.HTTPError: If the HTTP request fails after all retries
      ValueError: If the response format is invalid
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            timeout = httpx.Timeout(300.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": MODEL_NAME,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            # Lower temperature for more consistent JSON output
                            "temperature": 0.7,
                            "top_p": 0.9,
                        }
                    }
                )

                response.raise_for_status()
                response_data = response.json()

                if "response" not in response_data:
                    raise ValueError(
                        f"Invalid response format from Ollama: {response_data}"
                    )

                generated_text = response_data["response"]

                if not generated_text or not generated_text.strip():
                    raise ValueError("Empty response from LLM")

                logger.debug(f"LLM response received (attempt {attempt + 1})")
                return generated_text

        except httpx.HTTPError as e:
            last_error = e
            if attempt < max_retries - 1:
                # Exponential backoff
                wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"LLM request failed (attempt {attempt + 1}/{max_retries}): "
                    f"{str(e)}. Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"LLM request failed after {max_retries} attempts: {str(e)}"
                )
                raise
        except ValueError as e:
            # Don't retry on value errors (invalid response format)
            logger.error(f"Invalid LLM response format: {str(e)}")
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"Unexpected error in LLM request "
                    f"(attempt {attempt + 1}/{max_retries}): {str(e)}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"Unexpected error after {max_retries} attempts: {str(e)}",
                    exc_info=True
                )
                raise

    # Should never reach here, but just in case
    if last_error:
        raise last_error
    raise RuntimeError("Failed to generate text after all retries")
