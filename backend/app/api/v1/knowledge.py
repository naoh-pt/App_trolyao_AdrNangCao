"""Admin-only endpoints for importing the student handbook into RAG."""

import hmac
import sqlite3

from fastapi import APIRouter, Depends, File, Header, UploadFile, status

from app.config import RAG_ADMIN_TOKEN
from app.db.connection import get_db
from app.exceptions import AdminAuthorizationException, RAGUnavailableException
from app.schemas.knowledge import KnowledgeDocumentResponse
from app.services.rag_service import ingest_pdf

router = APIRouter(prefix="/knowledge", tags=["Knowledge base"])


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    """Do not expose handbook ingestion to ordinary app clients."""
    if not RAG_ADMIN_TOKEN or not x_admin_token or not hmac.compare_digest(x_admin_token, RAG_ADMIN_TOKEN):
        raise AdminAuthorizationException()


@router.post(
    "/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin_token)],
    summary="Import a text-based student-handbook PDF into RAG",
)
async def upload_document(
    file: UploadFile = File(...),
    db: sqlite3.Connection = Depends(get_db),
) -> KnowledgeDocumentResponse:
    if not file.filename:
        raise RAGUnavailableException("Thiếu tên file")
    data = await file.read()
    result = ingest_pdf(db, file.filename, data)
    return KnowledgeDocumentResponse(**result)


@router.get(
    "/documents",
    response_model=list[KnowledgeDocumentResponse],
    dependencies=[Depends(require_admin_token)],
    summary="List imported handbook documents",
)
def list_documents(db: sqlite3.Connection = Depends(get_db)) -> list[KnowledgeDocumentResponse]:
    rows = db.execute(
        "SELECT id, filename, page_count, chunk_count FROM knowledge_documents ORDER BY created_at DESC"
    ).fetchall()
    return [KnowledgeDocumentResponse(**dict(row)) for row in rows]
