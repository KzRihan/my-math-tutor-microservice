import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = os.getenv("MODEL_NAME", "llama3.1:8b")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "10m")

# Optional Ollama tuning knobs (set via env if needed)
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
OLLAMA_TOP_P = float(os.getenv("OLLAMA_TOP_P", "0.9"))
OLLAMA_NUM_CTX = os.getenv("OLLAMA_NUM_CTX")
OLLAMA_NUM_PREDICT = os.getenv("OLLAMA_NUM_PREDICT")

# Stable Diffusion (Automatic1111) configuration
SD_API_URL = os.getenv("SD_API_URL", "")
SD_TIMEOUT_SECONDS = float(os.getenv("SD_TIMEOUT_SECONDS", "60"))
SD_WIDTH = int(os.getenv("SD_WIDTH", "512"))
SD_HEIGHT = int(os.getenv("SD_HEIGHT", "512"))
SD_STEPS = int(os.getenv("SD_STEPS", "20"))
SD_CFG_SCALE = float(os.getenv("SD_CFG_SCALE", "7"))
SD_SAMPLER = os.getenv("SD_SAMPLER", "Euler a")
