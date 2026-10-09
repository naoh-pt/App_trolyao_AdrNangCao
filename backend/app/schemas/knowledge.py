"""Schemas for handbook ingestion and RAG citations."""

from pydantic import BaseModel


class SourceResponse(BaseModel):
    document_id: str
    filename: str
    page_number: int
    score: float


class KnowledgeDocumentResponse(BaseModel):
    id: str
    filename: str
    page_count: int
    chunk_count: int
