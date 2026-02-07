# Math Agent Base

A Math Tutor Service that provides intelligent, Socratic-method-based mathematics tutoring through conversational AI. The API uses Ollama for LLM interactions and Redis for session management, enabling personalized learning experiences with conversation history tracking.

## Project Structure

```
math-tutor-service/
|-- app/
|   |-- __init__.py
|   |-- main.py                 # FastAPI application factory
|   |-- core/
|   |   |-- __init__.py
|   |   `-- config.py           # Configuration settings
|   |-- models/
|   |   |-- __init__.py
|   |   `-- schemas.py          # Pydantic request/response models
|   |-- api/
|   |   |-- __init__.py
|   |   `-- v1/
|   |       |-- __init__.py
|   |       `-- routes.py       # API v1 routes
|   `-- services/
|       |-- __init__.py
|       |-- redis_service.py    # Redis session management
|       `-- ollama_service.py   # Ollama LLM service
|-- .env.example
|-- requirements.txt
|-- run.py                      # Application entry point
`-- README.md
```

## Features

- **Socratic Method Tutoring**: Guides students through mathematical problems using questions rather than direct answers
- **Adaptive Learning**: Automatically detects student grade level (Primary/Secondary/College) and adapts explanations accordingly
- **Conversation History**: Maintains session-based conversation context for personalized learning experiences
- **Streaming Responses**: Supports both streaming and non-streaming response modes for real-time interactions
- **Session Management**: Redis-backed session storage with configurable TTL
- **Grade-Level Adaptation**: Adjusts language, notation, and complexity based on detected student level
- **Safety Gates**: Prevents revealing complete solutions, ensuring students learn through guided discovery

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your actual configuration values
# Never commit .env to version control!
```

## Usage

### Running the Application

From the project root:

```bash
python run.py
```

Or using uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### API Endpoints

- `GET /` - Root endpoint with API information
- `GET /api/v1/health` - Health check endpoint
- `POST /api/v1/chat` - Chat endpoint (supports streaming)
- `DELETE /api/v1/session/{session_id}` - Delete a session

### Example Request

```python
import requests

# Non-streaming request
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "session_id": "session_123",
        "student_message": "How do I solve 2x + 5 = 15?",
        "stream": False
    }
)

print(response.json())
```

### Streaming Request

```python
import requests

# Streaming request
response = requests.post(
    "http://localhost:8000/api/v1/chat",
    json={
        "session_id": "session_123",
        "student_message": "Explain quadratic equations",
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode('utf-8'))
```

## Configuration

All configuration is done through environment variables. The application loads settings from a `.env` file in the `math-tutor-service` directory.

**Important Security Note**: Never commit `.env` files to version control. The `.gitignore` file is configured to exclude `.env` files. Always use `.env.example` as a template.

### Setting Up Environment Variables

1. Copy the example file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual values (especially passwords and API keys)

3. The `.env` file is automatically loaded when the application starts

### Available Configuration Variables

### Ollama Configuration

- `OLLAMA_CHAT_URL`: Ollama API endpoint (default: `http://0.0.0.0:11434/api/chat`)
- `MODEL_NAME`: Model to use for responses (default: `llama3.1:8b`)

### Redis Configuration

- `REDIS_HOST`: Redis host (default: `localhost`)
- `REDIS_PORT`: Redis port (default: `6379`)
- `REDIS_DB`: Redis database number (default: `0`)
- `REDIS_PASSWORD`: Redis password (default: `None`)
- `REDIS_DECODE_RESPONSES`: Whether to decode responses (default: `true`)
- `REDIS_SESSION_TTL`: Session expiration time in seconds (default: `3600`)

### CORS Configuration

- `CORS_ORIGINS`: Allowed CORS origins, comma-separated or `*` for all (default: `*`)
- `CORS_ALLOW_CREDENTIALS`: Allow credentials in CORS (default: `true`)

### API Configuration

- `API_TITLE`: API title (default: `Math Tutor Service`)
- `API_VERSION`: API version (default: `1.0.0`)

### RAG Configuration (Local Chroma)

- `RAG_ENABLED`: Enable retrieval-augmented generation (default: `true`)
- `RAG_DB_DIR`: Local directory for Chroma persistence (default: `rag_db`)
- `RAG_DOCS_DIR`: Directory of documents to ingest (default: `rag_docs`)
- `RAG_COLLECTION_NAME`: Chroma collection name (default: `math_tutor_rag`)
- `RAG_TOP_K`: Number of chunks to retrieve (default: `6`)
- `RAG_MIN_SCORE`: Minimum similarity score for context (default: `0.25`)
- `RAG_MAX_CONTEXT_CHARS`: Max context size injected into prompt (default: `4000`)
- `RAG_CHUNK_SIZE`: Chunk size in characters (default: `800`)
- `RAG_CHUNK_OVERLAP`: Overlap in characters between chunks (default: `120`)
- `RAG_AUTO_INGEST`: Auto-ingest on startup (default: `false`)
- `RAG_BATCH_SIZE`: Batch size for embeddings + inserts (default: `32`)

### Ollama Embeddings

- `OLLAMA_EMBED_URL`: Ollama embeddings endpoint (default: `http://0.0.0.0:11434/api/embeddings`)
- `OLLAMA_EMBED_MODEL`: Embedding model (default: `nomic-embed-text`)

## RAG Usage (Local Dev)

1) Put your knowledge files in `rag_docs/` (supports `.md`, `.txt`, `.json`, `.jsonl`).
2) Ingest them with the API:

```bash
curl -X POST http://localhost:8000/api/v1/rag/ingest \
  -H "Content-Type: application/json" \
  -d '{"rebuild": true}'
```

3) Start chatting as usual; relevant context will be injected automatically.

## How It Works

The Math Tutor API uses a structured teaching pipeline to guide students through mathematical concepts:

1. **Level Detection**: Analyzes the student's language and questions to determine their grade level
2. **Lesson Planning**: Identifies the next micro-objective for the student to learn
3. **Concept Teaching**: Provides age-appropriate explanations with LaTeX notation
4. **Guided Examples**: Walks through partial examples, converting steps into questions
5. **Practice Generation**: Creates related practice problems without solving them
6. **Hint Engine**: Provides minimal Socratic hints when students struggle
7. **Understanding Check**: Evaluates responses and redirects misconceptions
8. **Safety Gates**: Prevents revealing complete solutions or final answers
9. **Mastery Tracking**: Internally tracks student progress and adjusts difficulty
10. **Topic Progression**: Suggests next logical topics when mastery is demonstrated

The tutor never gives direct answers but instead guides students to discover solutions through thoughtful questions.

## Module Details

### `app/core/config.py`

Manages all configuration settings including Ollama endpoints, Redis connection details, and system prompts.

### `app/models/schemas.py`

Defines the API request/response models:

- `ChatRequest`: Student message and session information
- `ChatResponse`: Tutor's response message
- `HealthResponse`: Service health status

### `app/services/redis_service.py`

Handles conversation history storage and retrieval:

- Maintains session-based conversation context
- Manages session expiration and cleanup

### `app/services/ollama_service.py`

Integrates with Ollama LLM for generating tutor responses:

- Processes conversation history with system prompts
- Supports both streaming and non-streaming modes

### `app/api/v1/routes.py`

Exposes the REST API endpoints:

- Health check for service monitoring
- Chat endpoint for student-tutor interactions
- Session management for conversation history

### `app/main.py`

Initializes the FastAPI application with middleware and route configuration.

## Development

### Project Structure Benefits

1. **Scalability**: Easy to add new API versions (v2, v3, etc.)
2. **Maintainability**: Clear separation of concerns
3. **Testability**: Each module can be tested independently
4. **Flexibility**: Services can be easily swapped or extended

### Adding New Features

- **New API endpoints**: Add to `app/api/v1/routes.py` or create new version
- **New models**: Add to `app/models/schemas.py`
- **New services**: Add to `app/services/` directory
- **Configuration**: Add to `app/core/config.py`

## API Documentation

Once the server is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
