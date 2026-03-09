import httpx
import logging
import time

from app.config import (
    SD_API_URL,
    SD_TIMEOUT_SECONDS,
    SD_WIDTH,
    SD_HEIGHT,
    SD_STEPS,
    SD_CFG_SCALE,
    SD_SAMPLER,
    SD_VIDEO_ENDPOINTS,
)

logger = logging.getLogger(__name__)

_availability_cache = {
    "checked_at": 0.0,
    "ok": False,
}
_availability_ttl_seconds = 30.0


def is_enabled() -> bool:
    return bool(SD_API_URL)


async def is_available(force_check: bool = False) -> bool:
    if not SD_API_URL:
        return False

    now = time.time()
    if (
        not force_check
        and (now - _availability_cache["checked_at"]) < _availability_ttl_seconds
    ):
        return bool(_availability_cache["ok"])

    timeout = httpx.Timeout(5.0, connect=2.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{SD_API_URL}/sdapi/v1/options")
            ok = response.status_code == 200
    except Exception as e:
        logger.warning("Stable Diffusion API health check failed: %s", str(e))
        ok = False

    _availability_cache["checked_at"] = now
    _availability_cache["ok"] = ok
    return ok


async def generate_diagram(prompt: str) -> str | None:
    if not await is_available():
        return None

    payload = {
        "prompt": prompt,
        "width": SD_WIDTH,
        "height": SD_HEIGHT,
        "steps": SD_STEPS,
        "cfg_scale": SD_CFG_SCALE,
        "sampler_name": SD_SAMPLER,
        "negative_prompt": "blurry, low quality, text, watermark",
        "do_not_save_samples": True,
        "do_not_save_grid": True,
    }

    timeout = httpx.Timeout(SD_TIMEOUT_SECONDS, connect=10.0)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{SD_API_URL}/sdapi/v1/txt2img",
                json=payload
            )
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as e:
        body = ""
        try:
            body = e.response.text[:500]
        except Exception:
            body = ""
        logger.warning(
            "Stable Diffusion image generation failed (%s): %s",
            e.response.status_code if e.response else "unknown",
            body or str(e),
        )
        return None
    except Exception as e:
        logger.warning("Stable Diffusion image generation error: %s", str(e))
        return None

    images = data.get("images", [])
    if not images:
        logger.warning("Stable Diffusion returned no images")
        return None

    return images[0]


async def generate_video(prompt: str) -> str | None:
    if not await is_available():
        return None

    payload = {
        "prompt": prompt,
        "width": SD_WIDTH,
        "height": SD_HEIGHT,
        "steps": SD_STEPS,
        "cfg_scale": SD_CFG_SCALE,
        "sampler_name": SD_SAMPLER,
    }

    timeout = httpx.Timeout(SD_TIMEOUT_SECONDS, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for endpoint in SD_VIDEO_ENDPOINTS:
            url = f"{SD_API_URL}{endpoint}"
            try:
                response = await client.post(url, json=payload)
                if response.status_code == 404:
                    continue
                response.raise_for_status()
                data = response.json()
            except Exception:
                continue

            if isinstance(data, dict):
                if isinstance(data.get("video_url"), str):
                    return data["video_url"]
                if isinstance(data.get("url"), str):
                    return data["url"]
                videos = data.get("videos")
                if isinstance(videos, list) and videos and isinstance(videos[0], str):
                    return videos[0]
                if isinstance(data.get("video"), str):
                    return data["video"]

    return None
