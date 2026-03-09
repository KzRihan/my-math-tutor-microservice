# Syllabus Service API

A FastAPI microservice that generates **school-style syllabus content** using an open-source LLM (via Ollama). The service is designed to generate syllabus data **incrementally** to avoid token limits and improve reliability.

## âœ¨ Features

* Generate **lesson titles** for a given topic
* Generate **full lesson content** lesson-by-lesson
* Designed to avoid large LLM responses (chunked generation)
* Strong request/response validation using Pydantic
* Works locally on **Mac Mini M1 (16GB RAM)**
* Uses **Ollama + LLaMA** open-source models

---

## ðŸ— Architecture Overview

```
Frontend
  â”œâ”€â”€ Call /generate-lessons
  â”‚     â†’ Get lesson titles
  â”œâ”€â”€ Loop lessons
  â”‚     â””â”€â”€ Call /generate-lesson-content
  â”‚           â†’ Store lesson content
  â””â”€â”€ Assemble syllabus on frontend or backend
```

This approach ensures:

* No API response size limits
* Stateless backend
* Easy retries per lesson
* Horizontal scalability

---

## ðŸ“ Project Structure

```
math-syllabus-service/
|-- app/
|   |-- config.py        # Configuration
|   |-- diagram.py       # Stable Diffusion diagram helper
|   |-- llm.py           # Ollama LLM client
|   |-- main.py          # FastAPI routes
|   `-- models.py        # Pydantic schemas
|-- .venv/
|-- requirements.txt
`-- README.md
```

---

## âš™ï¸ Requirements

* Python 3.9+
* FastAPI
* Uvicorn
* Ollama
* Open-source LLM (tested with llama3.2:1b)

---

## ðŸ¤– LLM Setup (Ollama)

Install Ollama:

```
brew install ollama
```

Pull the model:

```
ollama pull llama3.1:8b
```

Start Ollama server:

```
ollama serve
```

Default configuration (`app/config.py`):

```python
OLLAMA_BASE_URL = "http://localhost:11434"
MODEL_NAME = "llama3.2:1b"
```

---

## â–¶ï¸ Running the Service

Create virtual environment:

```
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```
pip install fastapi uvicorn requests pydantic
```

Run the server:

```
uvicorn app.main:app --host 0.0.0.0 --port 8503
```

Swagger UI:

```
http://0.0.0.0:8503/docs
```

---

## ðŸ“Œ API Endpoints

### 1ï¸âƒ£ Generate Lesson Titles

**Endpoint**

```
POST /generate-lessons
```

**Request**

```json
{
  "topic_title": "Addition",
  "grade": "primary",
  "difficulty_level": "medium",
  "number_of_lessons": 5
}
```

**Response**

```json
{
  "topic": "Addition",
  "grade": "primary",
  "difficulty_level": "medium",
  "lessons": [
    "Understanding Addition",
    "Adding Single Digits",
    "Addition with Regrouping",
    "Word Problems in Addition",
    "Practice and Review"
  ]
}
```

---

### 2ï¸âƒ£ Generate Lesson Content

**Endpoint**

```
POST /generate-lesson-content
```

**Request**

```json
{
  "topic_title": "Addition",
  "lesson_title": "Adding Single Digits",
  "grade": "primary",
  "difficulty_level": "medium",
  "exercises_count": 2,
  "quiz_count": 2,
  "generate_images": true,
  "generate_videos": false
}
```

**Response**

```json
{
  "lesson": {
    "lesson_number": 1,
    "title": "Adding Single Digits",
    "introduction": "...",
    "explanation": "...",
    "worked_examples": [],
    "tips": [],
    "common_mistakes": [],
    "practice_exercises": [],
    "quiz": []
  }
}
```

---

## ðŸ§  Why Lesson-by-Lesson Generation?

* Prevents token overflow
* LLM does not need long-term memory
* Each lesson is deterministic and retryable
* Frontend controls pacing and storage

---

## ðŸ›¡ Best Practices Used

* Strict JSON-only LLM prompts
* Regex-based JSON extraction
* Pydantic validation for all I/O
* Stateless APIs (no server memory)
* Clear separation of concerns

---

## Stable Diffusion Media

Set these environment variables before starting the service:

```bash
SD_API_URL=http://127.0.0.1:7860
SD_TIMEOUT_SECONDS=120
SD_WIDTH=384
SD_HEIGHT=384
SD_STEPS=12
```

When `generate_images=true`, the service attempts to add generated visuals to worked examples, practice exercises, and quiz questions.

When `generate_videos=true`, the service attempts to call configured video endpoints (if supported by your Stable Diffusion extensions).

---

## ðŸš€ Scalability Notes

* Can be horizontally scaled (no shared state)
* Can swap LLM model without API changes
* Easy to add Redis or DB later
* Frontend can parallelize lesson generation

---

## ðŸ§ª Testing with curl

```bash
curl -X POST http://localhost:8503/generate-lessons \
  -H "Content-Type: application/json" \
  -d '{
    "topic_title": "Addition",
    "grade": "primary",
    "difficulty_level": "medium",
    "number_of_lessons": 3
  }'
```

