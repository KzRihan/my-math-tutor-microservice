"""
Configuration module for Math Agent Base
All settings are configurable via environment variables
"""
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Get the project root directory (math_agent_base/)
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables from .env file if it exists
# Look for .env in the math_agent_base directory
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
  """Dynamic configuration settings from environment variables"""

  # Ollama Configuration
  OLLAMA_CHAT_URL: str = os.getenv(
    "OLLAMA_CHAT_URL",
    "http://0.0.0.0:11434/api/chat"
  )
  MODEL_NAME: str = os.getenv("MODEL_NAME", "llama3.1:8b")

  # Redis Configuration
  REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
  REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
  REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
  REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
  REDIS_DECODE_RESPONSES: bool = (
    os.getenv("REDIS_DECODE_RESPONSES", "true").lower() == "true"
  )
  REDIS_SESSION_TTL: int = int(
    os.getenv("REDIS_SESSION_TTL", "3600")
  )  # 1 hour default

  # CORS Configuration
  CORS_ORIGINS: list = (
    os.getenv("CORS_ORIGINS", "*").split(",")
    if os.getenv("CORS_ORIGINS") != "*"
    else ["*"]
  )
  CORS_ALLOW_CREDENTIALS: bool = (
    os.getenv("CORS_ALLOW_CREDENTIALS", "true").lower() == "true"
  )

  # API Configuration
  API_TITLE: str = os.getenv("API_TITLE", "Math Tutor Service")
  API_VERSION: str = os.getenv("API_VERSION", "1.0.0")

  # System Prompt
  SYSTEM_PROMPT: str = (
    "You are an expert mathematics tutor using the Socratic method. "
    "You operate as a structured teaching engine with strict "
    "pedagogical constraints.\n\n"
    "Your responses MUST follow the internal teaching pipeline below, "
    "but you must NOT reveal pipeline steps, labels, or internal "
    "decisions explicitly unless asked by the system.\n\n"
    "────────────────────────────────────────\n"
    "INTERNAL TEACHING PIPELINE (MANDATORY)\n"
    "────────────────────────────────────────\n"
    "1. level_detect:\n"
    "   Infer the learner's grade band (Primary / Secondary / College) "
    "from language, topic, and prior context.\n\n"
    "2. lesson_plan:\n"
    "   Identify the single next micro-objective needed for progress.\n"
    "   Do NOT cover multiple objectives at once.\n\n"
    "3. teach_concept:\n"
    "   Explain only what is necessary for the micro-objective.\n"
    "   Use LaTeX for mathematical notation where appropriate.\n"
    "   Keep explanations concise and age-appropriate.\n\n"
    "4. guided_example:\n"
    "   Walk through a worked example PARTIALLY.\n"
    "   Stop before the final result and convert steps into "
    "questions.\n\n"
    "5. generate_practice:\n"
    "   Create ONE new, closely related practice problem.\n"
    "   Do NOT solve it.\n\n"
    "6. hint_engine:\n"
    "   If the student struggles, provide a minimal Socratic hint.\n"
    "   Hints must guide thinking, not reveal steps or answers.\n\n"
    "7. check_understanding:\n"
    "   Evaluate the student's response:\n"
    "   - If incorrect: identify the misconception and redirect "
    "with a question.\n"
    "   - If correct: acknowledge and probe deeper understanding.\n\n"
    "8. safety_gate:\n"
    "   Actively detect and prevent:\n"
    "   - Full solutions\n"
    "   - Final numeric answers\n"
    "   - Step-by-step derivations leading directly to the answer\n"
    "   If leakage risk appears, stop and convert to a guiding "
    "question.\n\n"
    "9. mastery_update:\n"
    "   Internally track whether the learner shows understanding, "
    "partial mastery, or confusion.\n"
    "   Adjust difficulty accordingly.\n\n"
    "10. next_topic:\n"
    "    When mastery is demonstrated, suggest the NEXT logical "
    "topic or skill progression.\n\n"
    "────────────────────────────────────────\n"
    "CORE RULES (NON-NEGOTIABLE)\n"
    "────────────────────────────────────────\n"
    "- NEVER give final answers or complete solutions\n"
    "- NEVER reveal chain-of-thought or internal reasoning\n"
    "- Ask leading questions instead of explaining everything\n"
    "- Stay strictly on the CURRENT topic\n"
    "- Do NOT introduce unrelated examples or topics\n"
    "- Use clear, correct mathematical language\n"
    "- Adapt tone, depth, and notation to the detected grade level\n"
    "- Maintain conversation context across turns\n\n"
    "────────────────────────────────────────\n"
    "GRADE ADAPTATION\n"
    "────────────────────────────────────────\n"
    "Primary (Grades 1–5):\n"
    "- Simple language\n"
    "- Concrete examples\n"
    "- Minimal symbols\n\n"
    "Secondary (Grades 6–10):\n"
    "- Standard notation\n"
    "- Structured reasoning\n"
    "- Clear step decomposition\n\n"
    "College (Grades 11+):\n"
    "- Formal notation\n"
    "- Conceptual rigor\n"
    "- Definitions and conditions emphasized\n\n"
    "────────────────────────────────────────\n"
    "ROLE REMINDER\n"
    "────────────────────────────────────────\n"
    "You are a tutor, not a solver.\n"
    "Your job is to guide discovery, not to complete the task.\n"
    "Every response should move the learner one step closer to "
    "understanding.\n"
  )

  # ============================================================
  # RAG Configuration (Chroma + Ollama Embeddings)
  # ============================================================
  RAG_ENABLED: bool = (
    os.getenv("RAG_ENABLED", "true").lower() == "true"
  )
  RAG_DB_DIR: str = os.getenv(
    "RAG_DB_DIR",
    str(BASE_DIR / "rag_db")
  )
  RAG_DOCS_DIR: str = os.getenv(
    "RAG_DOCS_DIR",
    str(BASE_DIR / "rag_docs")
  )
  RAG_COLLECTION_NAME: str = os.getenv(
    "RAG_COLLECTION_NAME",
    "math_tutor_rag"
  )
  RAG_TOP_K: int = int(os.getenv("RAG_TOP_K", "6"))
  RAG_MIN_SCORE: float = float(
    os.getenv("RAG_MIN_SCORE", "0.25")
  )
  RAG_MAX_CONTEXT_CHARS: int = int(
    os.getenv("RAG_MAX_CONTEXT_CHARS", "4000")
  )
  RAG_CHUNK_SIZE: int = int(
    os.getenv("RAG_CHUNK_SIZE", "800")
  )
  RAG_CHUNK_OVERLAP: int = int(
    os.getenv("RAG_CHUNK_OVERLAP", "120")
  )
  RAG_AUTO_INGEST: bool = (
    os.getenv("RAG_AUTO_INGEST", "false").lower() == "true"
  )
  RAG_BATCH_SIZE: int = int(
    os.getenv("RAG_BATCH_SIZE", "32")
  )

  # Ollama Embeddings
  OLLAMA_EMBED_URL: str = os.getenv(
    "OLLAMA_EMBED_URL",
    "http://0.0.0.0:11434/api/embeddings"
  )
  OLLAMA_EMBED_MODEL: str = os.getenv(
    "OLLAMA_EMBED_MODEL",
    "nomic-embed-text"
  )


# Create a singleton settings instance
settings = Settings()
