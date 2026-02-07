"""
Pydantic models for request/response schemas
"""
from typing import Any, Dict, List, Optional

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


class RagIngestDocument(BaseModel):
  """Single document to ingest into the RAG index"""
  text: str = Field(..., description="Raw text content")
  metadata: Dict[str, Any] = Field(
    default_factory=dict,
    description="Optional metadata for filtering or attribution"
  )
  id: Optional[str] = Field(
    default=None,
    description="Optional stable document ID"
  )


class RagIngestRequest(BaseModel):
  """Request model for RAG ingestion"""
  documents: Optional[List[RagIngestDocument]] = Field(
    default=None,
    description="Optional list of documents to ingest"
  )
  source_dir: Optional[str] = Field(
    default=None,
    description="Optional local directory to ingest"
  )
  rebuild: bool = Field(
    default=False,
    description="Whether to rebuild the index from scratch"
  )


class RagIngestResponse(BaseModel):
  """Response model for RAG ingestion"""
  indexed_documents: int = Field(
    ..., description="Number of documents indexed"
  )
  indexed_chunks: int = Field(
    ..., description="Number of chunks stored"
  )
  source: str = Field(
    ..., description="Ingestion source"
  )
