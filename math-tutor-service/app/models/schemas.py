"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
  """Request model for chat endpoint"""
  session_id: str = Field(
    ..., description="Unique session identifier"
  )
  student_message: str = Field(
    ..., description="Student's message/question"
  )
  stream: bool = Field(
    default=False, description="Whether to stream the response"
  )

  class Config:
    json_schema_extra = {
      "example": {
        "session_id": "session_123",
        "student_message": "How do I solve 2x + 5 = 15?",
        "stream": False
      }
    }


class ChatResponse(BaseModel):
  """Response model for chat endpoint"""
  agent_message: str = Field(
    ..., description="Tutor's response message"
  )

  class Config:
    json_schema_extra = {
      "example": {
        "agent_message": (
          "Let's think about this step by step. "
          "What operation would you use to isolate x?"
        )
      }
    }


class HealthResponse(BaseModel):
  """Response model for health check endpoint"""
  status: str = Field(
    default="healthy", description="Service health status"
  )

  class Config:
    json_schema_extra = {
      "example": {
        "status": "healthy"
      }
    }
