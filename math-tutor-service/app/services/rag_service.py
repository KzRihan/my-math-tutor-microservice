"""
RAG service module for retrieval-augmented generation
Uses ChromaDB for vector storage and Ollama embeddings
"""
import json
import logging
import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import chromadb
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RagChunk:
  """Single retrieved chunk with metadata and similarity score"""
  text: str
  metadata: Dict[str, str]
  score: float


@dataclass
class RagIngestResult:
  """Ingestion summary"""
  documents: int
  chunks: int
  source: str


class RagService:
  """RAG service for ingesting documents and retrieving context"""

  def __init__(self) -> None:
    self.base_dir = Path(__file__).resolve().parent.parent.parent
    self.enabled = settings.RAG_ENABLED
    self.db_dir = self._resolve_path(settings.RAG_DB_DIR)
    self.docs_dir = self._resolve_path(settings.RAG_DOCS_DIR)
    self.collection_name = settings.RAG_COLLECTION_NAME
    self.top_k = settings.RAG_TOP_K
    self.min_score = settings.RAG_MIN_SCORE
    self.max_context_chars = settings.RAG_MAX_CONTEXT_CHARS
    self.chunk_size = settings.RAG_CHUNK_SIZE
    self.chunk_overlap = settings.RAG_CHUNK_OVERLAP
    self.batch_size = settings.RAG_BATCH_SIZE

    self._client: Optional[chromadb.PersistentClient] = None
    self._collection = None

  def _resolve_path(self, path_value: str) -> str:
    path = Path(path_value)
    if path.is_absolute():
      return str(path)
    return str(self.base_dir / path_value)

  def _client_instance(self) -> chromadb.PersistentClient:
    if self._client is None:
      os.makedirs(self.db_dir, exist_ok=True)
      self._client = chromadb.PersistentClient(path=self.db_dir)
    return self._client

  def _collection_instance(self):
    if self._collection is None:
      client = self._client_instance()
      self._collection = client.get_or_create_collection(
        name=self.collection_name,
        metadata={"hnsw:space": "cosine"},
      )
    return self._collection

  async def _embed(self, text: str) -> List[float]:
    payload = {
      "model": settings.OLLAMA_EMBED_MODEL,
      "prompt": text,
    }
    async with httpx.AsyncClient() as client:
      resp = await client.post(settings.OLLAMA_EMBED_URL, json=payload)
      resp.raise_for_status()
      data = resp.json()
      embedding = data.get("embedding")
      if not embedding:
        raise ValueError("No embedding returned from Ollama")
      return embedding

  def _chunk_text(self, text: str) -> List[str]:
    clean = " ".join(text.strip().split())
    if not clean:
      return []
    if len(clean) <= self.chunk_size:
      return [clean]

    chunks = []
    start = 0
    length = len(clean)
    while start < length:
      end = start + self.chunk_size
      chunk = clean[start:end]
      if chunk:
        chunks.append(chunk)
      if end >= length:
        break
      start = max(0, end - self.chunk_overlap)
    return chunks

  def _read_docs_from_dir(self, source_dir: Optional[str]) -> List[Dict]:
    base_dir = Path(source_dir or self.docs_dir)
    if not base_dir.exists():
      logger.warning("RAG docs directory not found: %s", base_dir)
      return []

    documents: List[Dict] = []
    for path in base_dir.rglob("*"):
      if path.is_dir():
        continue
      ext = path.suffix.lower()
      try:
        if ext in (".txt", ".md"):
          text = path.read_text(encoding="utf-8")
          documents.append({
            "text": text,
            "metadata": {"source": str(path)},
          })
        elif ext == ".jsonl":
          for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
              continue
            item = json.loads(line)
            if "text" in item:
              documents.append({
                "text": item["text"],
                "metadata": item.get("metadata", {}),
              })
        elif ext == ".json":
          data = json.loads(path.read_text(encoding="utf-8"))
          if isinstance(data, list):
            for item in data:
              if isinstance(item, dict) and "text" in item:
                documents.append({
                  "text": item["text"],
                  "metadata": item.get("metadata", {}),
                })
          elif isinstance(data, dict):
            docs = data.get("documents") or data.get("docs") or []
            for item in docs:
              if isinstance(item, dict) and "text" in item:
                documents.append({
                  "text": item["text"],
                  "metadata": item.get("metadata", {}),
                })
      except Exception as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        continue

    return documents

  async def ingest_documents(
    self,
    documents: List[Dict],
    rebuild: bool = False,
    source: str = "documents"
  ) -> RagIngestResult:
    if not self.enabled:
      return RagIngestResult(documents=0, chunks=0, source=source)

    client = self._client_instance()
    if rebuild:
      try:
        client.delete_collection(self.collection_name)
      except Exception:
        pass
      self._collection = None

    collection = self._collection_instance()
    total_chunks = 0
    total_docs = 0

    batch_docs: List[str] = []
    batch_embeddings: List[List[float]] = []
    batch_metadatas: List[Dict] = []
    batch_ids: List[str] = []

    async def flush_batch():
      nonlocal batch_docs, batch_embeddings, batch_metadatas, batch_ids
      if not batch_docs:
        return
      collection.add(
        documents=batch_docs,
        embeddings=batch_embeddings,
        metadatas=batch_metadatas,
        ids=batch_ids,
      )
      batch_docs = []
      batch_embeddings = []
      batch_metadatas = []
      batch_ids = []

    for doc in documents:
      text = doc.get("text", "")
      if not text.strip():
        continue
      metadata = doc.get("metadata", {}) or {}
      doc_id = str(doc.get("id") or uuid.uuid4())

      chunks = self._chunk_text(text)
      if not chunks:
        continue
      total_docs += 1

      for idx, chunk in enumerate(chunks):
        try:
          embedding = await self._embed(chunk)
        except Exception as exc:
          logger.warning("Embedding failed for chunk: %s", exc)
          continue

        chunk_meta = {
          **metadata,
          "doc_id": doc_id,
          "chunk_index": idx,
          "source": metadata.get("source", source),
        }
        chunk_id = f"{doc_id}-{idx}"

        batch_docs.append(chunk)
        batch_embeddings.append(embedding)
        batch_metadatas.append(chunk_meta)
        batch_ids.append(chunk_id)
        total_chunks += 1

        if len(batch_docs) >= self.batch_size:
          await flush_batch()

    await flush_batch()
    return RagIngestResult(
      documents=total_docs,
      chunks=total_chunks,
      source=source,
    )

  async def ingest_directory(
    self,
    source_dir: Optional[str] = None,
    rebuild: bool = False
  ) -> RagIngestResult:
    documents = self._read_docs_from_dir(source_dir)
    source = source_dir or self.docs_dir
    return await self.ingest_documents(
      documents=documents,
      rebuild=rebuild,
      source=str(source),
    )

  async def retrieve(self, query: str) -> List[RagChunk]:
    if not self.enabled:
      return []
    if not query or not query.strip():
      return []

    try:
      embedding = await self._embed(query)
    except Exception as exc:
      logger.warning("Query embedding failed: %s", exc)
      return []

    collection = self._collection_instance()
    try:
      results = collection.query(
        query_embeddings=[embedding],
        n_results=self.top_k,
        include=["documents", "metadatas", "distances", "ids"],
      )
    except Exception as exc:
      logger.warning("Chroma query failed: %s", exc)
      return []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    chunks: List[RagChunk] = []
    for doc, meta, distance in zip(documents, metadatas, distances):
      if doc is None:
        continue
      # For cosine distance, similarity = 1 - distance
      score = 1 - distance if distance is not None else 0
      if score < self.min_score:
        continue
      chunks.append(RagChunk(text=doc, metadata=meta or {}, score=score))

    return chunks

  def build_context(self, chunks: List[RagChunk]) -> str:
    if not chunks:
      return ""
    lines: List[str] = []
    for idx, chunk in enumerate(chunks, start=1):
      source = chunk.metadata.get("source", "unknown")
      lines.append(
        f"[{idx}] Source: {source} | Score: {chunk.score:.2f}"
      )
      lines.append(chunk.text)
      lines.append("")
      if sum(len(line) for line in lines) >= self.max_context_chars:
        break

    context = "\n".join(lines).strip()
    if len(context) > self.max_context_chars:
      context = context[:self.max_context_chars]
    return context

  async def get_context_message(self, query: str) -> Optional[str]:
    chunks = await self.retrieve(query)
    context = self.build_context(chunks)
    if not context:
      return None

    return (
      "CONTEXT (use if relevant; do NOT fabricate details):\n"
      f"{context}\n\n"
      "Use the context to guide your Socratic tutoring. "
      "If the context does not contain the needed info, "
      "say so and continue with guided questions."
    )


# Create a singleton RAG service instance
rag_service = RagService()
