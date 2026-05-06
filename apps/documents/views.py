"""
LexAI document views.
"""
from __future__ import annotations

import uuid

import structlog
from kombu.exceptions import OperationalError
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.views import APIView

from apps.core.response import api_response
from apps.documents.models import DocumentChunk, LegalDocument
from apps.documents.serializers import (
    DocumentDetailSerializer,
    DocumentStatusSerializer,
    DocumentUploadSerializer,
    SessionDocumentSerializer,
)
from apps.documents.services.ingestion import ingest_document
from apps.documents.tasks import process_document_pipeline
from apps.vector_store.repository import VectorRepository

logger = structlog.get_logger(__name__)


class SessionCreateView(APIView):
    """POST /api/v1/sessions/ - create a new session id."""

    def post(self, request):
        session_id = uuid.uuid4()
        return api_response(
            data={
                "session_id": str(session_id),
                "id": str(session_id),
            },
            status_code=status.HTTP_201_CREATED,
        )


class DocumentUploadView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        session_id = str(data.get("session_id") or uuid.uuid4())

        document, is_duplicate = ingest_document(
            file=data["file"],
            title=data["title"],
            document_type=data["document_type"],
            session_id=session_id,
        )

        if is_duplicate:
            return api_response(
                data={
                    "document_id": str(document.id),
                    "session_id": str(document.session_id),
                    "title": document.title,
                    "status": document.status,
                    "duplicate": True,
                },
                status_code=status.HTTP_200_OK,
            )

        try:
            result = process_document_pipeline(str(document.id))
        except OperationalError as exc:
            logger.error("pipeline_dispatch_failed", document_id=str(document.id), error=str(exc))
            document.status = LegalDocument.ProcessingStatus.FAILED
            document.processing_error = "Queue unavailable: could not connect to Redis/Celery broker"
            document.save(update_fields=["status", "processing_error", "updated_at"])
            return api_response(
                success=False,
                error="Task queue unavailable. Start Redis and Celery worker, then upload again.",
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return api_response(
            data={
                "document_id": str(document.id),
                "session_id": str(document.session_id),
                "title": document.title,
                "status": document.status,
                "task_id": result.id,
            },
            status_code=status.HTTP_202_ACCEPTED,
        )


class DocumentStatusView(APIView):
    def get(self, request, document_id):
        try:
            document = LegalDocument.objects.get(id=document_id)
        except LegalDocument.DoesNotExist:
            return api_response(
                error="Document not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = DocumentStatusSerializer(document)
        return api_response(data=serializer.data)


class DocumentDetailView(APIView):
    def get(self, request, document_id):
        try:
            document = LegalDocument.objects.get(id=document_id)
        except LegalDocument.DoesNotExist:
            return api_response(
                error="Document not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = DocumentDetailSerializer(document)
        return api_response(data=serializer.data)


class DocumentDeleteView(APIView):
    def delete(self, request, document_id):
        try:
            document = LegalDocument.objects.get(id=document_id)
        except LegalDocument.DoesNotExist:
            return api_response(
                error="Document not found",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            repo = VectorRepository()
            repo.delete_by_document_id(str(document.session_id), str(document.id))
        except Exception as exc:
            logger.warning("vector_cleanup_failed", error=str(exc))

        document.chunks.all().update(deleted_at=document.updated_at)
        document.delete()

        return api_response(
            data={"document_id": str(document_id), "deleted": True},
            status_code=status.HTTP_200_OK,
        )


class SessionDocumentsView(APIView):
    def get(self, request, session_id):
        documents = (
            LegalDocument.objects.filter(session_id=session_id)
            .order_by("-created_at")
        )
        serializer = SessionDocumentSerializer(documents, many=True)
        return api_response(data=serializer.data)


class SessionStatsView(APIView):
    def get(self, request, session_id):
        documents = LegalDocument.objects.filter(session_id=session_id)
        total_docs = documents.count()
        ready_docs = documents.filter(
            status=LegalDocument.ProcessingStatus.READY
        ).count()
        total_chunks = DocumentChunk.objects.filter(document__session_id=session_id).count()

        vector_count = 0
        collection_name = ""
        try:
            repo = VectorRepository()
            stats = repo.collection_stats(str(session_id))
            vector_count = stats.get("vector_count", 0)
            collection_name = stats.get("collection_name", "")
        except Exception:
            pass

        return api_response(
            data={
                "document_count": total_docs,
                "ready_document_count": ready_docs,
                "total_vectors": vector_count,
                "total_chunks": total_chunks,
                "collection_name": collection_name,
            }
        )


class SessionDeleteView(APIView):
    def delete(self, request, session_id):
        documents = LegalDocument.objects.filter(session_id=session_id)

        if not documents.exists():
            return api_response(
                error="Session not found or empty",
                status_code=status.HTTP_404_NOT_FOUND,
            )

        try:
            repo = VectorRepository()
            repo.delete_collection(str(session_id))
        except Exception as exc:
            logger.warning("session_collection_delete_failed", error=str(exc))

        doc_ids = list(documents.values_list("id", flat=True))
        DocumentChunk.objects.filter(document_id__in=doc_ids).delete()
        for doc in documents:
            doc.delete()

        return api_response(
            data={
                "session_id": str(session_id),
                "documents_deleted": len(doc_ids),
            },
            status_code=status.HTTP_200_OK,
        )
