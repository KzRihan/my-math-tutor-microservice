import httpx
import logging
import asyncio
from app.config import (
    OLLAMA_BASE_URL,
    MODEL_NAME,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_CONNECT_TIMEOUT_SECONDS,
    OLLAMA_READ_TIMEOUT_SECONDS,
    OLLAMA_MAX_RETRIES,
    OLLAMA_RETRY_DELAY_BASE,
    OLLAMA_TEMPERATURE,
    OLLAMA_TOP_P,
    OLLAMA_NUM_CTX,
    OLLAMA_NUM_PREDICT,
)

logger = logging.getLogger(__name__)

async def generate_text(prompt: str, max_retries: int = OLLAMA_MAX_RETRIES) -> str:
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
            timeout = httpx.Timeout(
                connect=OLLAMA_CONNECT_TIMEOUT_SECONDS,
                read=OLLAMA_READ_TIMEOUT_SECONDS,
                write=60.0,
                pool=60.0,
            )
            options = {
                "temperature": OLLAMA_TEMPERATURE,
                "top_p": OLLAMA_TOP_P,
            }
            if OLLAMA_NUM_CTX:
                options["num_ctx"] = int(OLLAMA_NUM_CTX)
            if OLLAMA_NUM_PREDICT:
                options["num_predict"] = int(OLLAMA_NUM_PREDICT)

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{OLLAMA_BASE_URL}/api/generate",
                    json={
                        "model": MODEL_NAME,
                        "prompt": prompt,
                        "stream": False,
                        "keep_alive": OLLAMA_KEEP_ALIVE,
                        "options": options,
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
                wait_time = OLLAMA_RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"LLM request failed (attempt {attempt + 1}/{max_retries}): "
                    f"{repr(e)}. Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    f"LLM request failed after {max_retries} attempts: {repr(e)}"
                )
                raise
        except ValueError as e:
            # Don't retry on value errors (invalid response format)
            logger.error(f"Invalid LLM response format: {str(e)}")
            raise
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = OLLAMA_RETRY_DELAY_BASE * (2 ** attempt)
                logger.warning(
                    f"Unexpected error in LLM request "
                    f"(attempt {attempt + 1}/{max_retries}): {repr(e)}. "
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
