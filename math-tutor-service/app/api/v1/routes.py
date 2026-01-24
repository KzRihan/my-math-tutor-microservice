"""
API v1 routes for Math Agent Base
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.models.schemas import (
  ChatRequest,
  ChatResponse,
  HealthResponse,
)
from app.services.redis_service import redis_service
from app.services.ollama_service import ollama_service
from app.core.config import settings

# Create router
router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
  """
  Health check endpoint

  Returns:
    Health status of the service
  """
  # Check Redis connection
  redis_status = redis_service.ping()

  if not redis_status:
    raise HTTPException(
      status_code=503,
      detail="Redis connection failed"
    )

  return HealthResponse(status="healthy")


@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest):
  """
  Chat endpoint for non-streaming responses

  Args:
    request: Chat request with session_id, student_message,
      and stream flag

  Returns:
    Chat response with agent message
  """
  # Load conversation history
  history = redis_service.load_history(request.session_id)

  # Add user message to history
  history.append({
    "role": "user",
    "content": request.student_message,
  })

  # Prepare messages with system prompt
  messages = [
    {"role": "system", "content": settings.SYSTEM_PROMPT},
    *history,
  ]

  # Handle streaming vs non-streaming
  if request.stream:
    # Return streaming response
    async def event_stream():
      full_response = ""

      try:
        async for token in ollama_service.stream(messages):
          full_response += token
          yield f"data: {token}\n\n"

        # Save history after streaming completes
        history.append({
          "role": "assistant",
          "content": full_response,
        })
        redis_service.save_history(request.session_id, history)
        yield "data: [DONE]\n\n"
      except Exception as e:
        yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(
      event_stream(),
      media_type="text/event-stream",
    )
  else:
    # Non-streaming response
    try:
      assistant_msg = await ollama_service.call(messages)

      # Add assistant response to history
      history.append({
        "role": "assistant",
        "content": assistant_msg,
      })

      # Save updated history
      redis_service.save_history(request.session_id, history)

      return ChatResponse(agent_message=assistant_msg)
    except Exception as e:
      raise HTTPException(
        status_code=500,
        detail=f"Error calling Ollama API: {str(e)}"
      )


@router.delete("/session/{session_id}", tags=["Session"])
async def delete_session(session_id: str):
  """
  Delete a session and its history

  Args:
    session_id: Unique session identifier

  Returns:
    Success message
  """
  success = redis_service.delete_session(session_id)

  if not success:
    raise HTTPException(
      status_code=404,
      detail=f"Session {session_id} not found"
    )

  return {"message": f"Session {session_id} deleted successfully"}
