import httpx
import logging

from app.config import (
    SD_API_URL,
    SD_TIMEOUT_SECONDS,
    SD_WIDTH,
    SD_HEIGHT,
    SD_STEPS,
    SD_CFG_SCALE,
    SD_SAMPLER,
)

logger = logging.getLogger(__name__)


def is_enabled() -> bool:
    return bool(SD_API_URL)


async def generate_diagram(prompt: str) -> str | None:
    if not SD_API_URL:
        return None

    payload = {
        "prompt": prompt,
        "width": SD_WIDTH,
        "height": SD_HEIGHT,
        "steps": SD_STEPS,
        "cfg_scale": SD_CFG_SCALE,
        "sampler_name": SD_SAMPLER,
        "negative_prompt": "blurry, low quality, text, watermark",
    }

    timeout = httpx.Timeout(SD_TIMEOUT_SECONDS, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(f"{SD_API_URL}/sdapi/v1/txt2img", json=payload)
        response.raise_for_status()
        data = response.json()

    images = data.get("images", [])
    if not images:
        logger.warning("Stable Diffusion returned no images")
        return None

    return images[0]
