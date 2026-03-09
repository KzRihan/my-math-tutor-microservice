import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")
OLLAMA_CONNECT_TIMEOUT_SECONDS = float(
  os.getenv("OLLAMA_CONNECT_TIMEOUT_SECONDS", "20")
)
OLLAMA_READ_TIMEOUT_SECONDS = float(
  os.getenv("OLLAMA_READ_TIMEOUT_SECONDS", "900")
)
OLLAMA_MAX_RETRIES = int(os.getenv("OLLAMA_MAX_RETRIES", "3"))
OLLAMA_RETRY_DELAY_BASE = float(os.getenv("OLLAMA_RETRY_DELAY_BASE", "1"))

# Optional Ollama tuning knobs (set via env if needed)
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
OLLAMA_NUM_CTX = os.getenv("OLLAMA_NUM_CTX")
OLLAMA_NUM_PREDICT = os.getenv("OLLAMA_NUM_PREDICT", "2048")

# Stable Diffusion (Automatic1111) configuration
SD_API_URL = os.getenv("SD_API_URL", "http://127.0.0.1:7860")
SD_TIMEOUT_SECONDS = float(os.getenv("SD_TIMEOUT_SECONDS", "120"))
SD_WIDTH = int(os.getenv("SD_WIDTH", "384"))
SD_HEIGHT = int(os.getenv("SD_HEIGHT", "384"))
SD_STEPS = int(os.getenv("SD_STEPS", "12"))
SD_CFG_SCALE = float(os.getenv("SD_CFG_SCALE", "7"))
SD_SAMPLER = os.getenv("SD_SAMPLER", "Euler a")

# Optional video endpoints (extension-dependent)
SD_VIDEO_ENDPOINTS = [
  e.strip() for e in os.getenv(
    "SD_VIDEO_ENDPOINTS",
    "/sdapi/v1/txt2video,/sdapi/v1/txt2vid,/sdapi/v1/text2video"
  ).split(",") if e.strip()
]
