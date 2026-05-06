"""
LexAI — Celery Tasks for Document Processing Pipeline

Pipeline: OCR → Chunk & Tag → Embed & Index
Wired as a Celery chain. Django views trigger the chain and return 202 Accepted.
"""
from __future__ import annotations

import time
from pathlib import Path

import structlog
from celery import shared_task, chain
from celery.result import AsyncResult

from apps.core.exceptions import DocumentProcessingError

logger = structlog.get_logger(__name__)


def _get_document(document_id: str):
    """Fetch LegalDocument by ID. Raises DocumentProcessingError if not found."""
    from apps.documents.models import LegalDocument
    try:
        return LegalDocument.objects.get(id=document_id)
    except LegalDocument.DoesNotExist:
        raise DocumentProcessingError(
            message=f"Document not found: {document_id}",
        )


def _extract_document_id(arg) -> str:
    """Extract document_id from either a string or dict (chain result)."""
    if isinstance(arg, dict):
        return arg["document_id"]
    return str(arg)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def task_run_ocr(self, document_id_or_result) -> dict:
    """
    Step 1: Run OCR on the document.

    1. Fetch LegalDocument from DB
    2. Set status = OCR_PROCESSING
    3. Call get_ocr_engine(mime_type).extract(file_path)
    4. Save raw_text, page_count, ocr_engine_used
    5. Set status = OCR_COMPLETE
    """
    document_id = _extract_document_id(document_id_or_result)
    log = logger.bind(task_id=self.request.id, document_id=document_id)
    log.info("task_run_ocr_start")
    start_time = time.time()

    try:
        from apps.documents.models import LegalDocument
        from infrastructure.ocr.factory import get_ocr_engine

        document = _get_document(document_id)
        document.status = LegalDocument.ProcessingStatus.OCR_PROCESSING
        document.save(update_fields=["status", "updated_at"])

        file_path = Path(document.file.path)
        engine = get_ocr_engine(document.mime_type)
        ocr_result = engine.extract(file_path)

        document.raw_text = ocr_result.raw_text
        document.page_count = ocr_result.page_count
        document.ocr_engine_used = ocr_result.engine_used
        document.status = LegalDocument.ProcessingStatus.OCR_COMPLETE
        document.save(update_fields=[
            "raw_text", "page_count", "ocr_engine_used", "status", "updated_at"
        ])

        duration = time.time() - start_time
        log.info("task_run_ocr_complete", duration=duration, pages=ocr_result.page_count)

        return {
            "document_id": document_id,
            "page_count": ocr_result.page_count,
            "char_count": len(ocr_result.raw_text),
        }

    except DocumentProcessingError:
        raise
    except Exception as exc:
        log.error("task_run_ocr_failed", error=str(exc))
        try:
            from apps.documents.models import LegalDocument
            doc = _get_document(document_id)
            doc.status = LegalDocument.ProcessingStatus.FAILED
            doc.processing_error = str(exc)
            doc.save(update_fields=["status", "processing_error", "updated_at"])
        except Exception:
            pass
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def task_chunk_and_tag(self, document_id_or_result) -> dict:
    """
    Step 2: Chunk the document and generate lineage metadata.

    1. Fetch LegalDocument (must be OCR_COMPLETE)
    2. Set status = CHUNKING
    3. Run LegalDocumentChunker
    4. Create DocumentChunk records + LineageMetadata
    5. Set status = EMBEDDING
    """
    document_id = _extract_document_id(document_id_or_result)
    log = logger.bind(task_id=self.request.id, document_id=document_id)
    log.info("task_chunk_and_tag_start")
    start_time = time.time()

    try:
        from apps.documents.models import LegalDocument, DocumentChunk
        from apps.documents.services.chunking import LegalDocumentChunker
        from apps.documents.services.lineage import (
            generate_lineage,
            generate_chroma_vector_id,
            generate_text_hash,
        )
        from infrastructure.ocr.base import OCRResult

        document = _get_document(document_id)
        document.status = LegalDocument.ProcessingStatus.CHUNKING
        document.save(update_fields=["status", "updated_at"])

        # Reconstruct OCRResult from stored data
        page_texts = document.raw_text.split("\n\n") if document.raw_text else []
        ocr_result = OCRResult(
            raw_text=document.raw_text,
            page_texts=page_texts,
            page_count=document.page_count or 1,
            engine_used=document.ocr_engine_used,
        )

        chunker = LegalDocumentChunker()
        chunks = chunker.chunk(ocr_result)

        created_count = 0
        for chunk in chunks:
            chroma_vector_id = generate_chroma_vector_id(
                str(document.id), chunk.chunk_index
            )
            text_hash = generate_text_hash(chunk.text)

            db_chunk = DocumentChunk.objects.create(
                document=document,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.text,
                page_number=chunk.page_number,
                section_label=chunk.section_label,
                char_start=chunk.char_start,
                char_end=chunk.char_end,
                text_hash=text_hash,
                chroma_vector_id=chroma_vector_id,
                token_count=chunk.token_count,
                is_embedded=False,
            )

            # Generate lineage (stored for later use during embedding)
            generate_lineage(chunk, document, str(db_chunk.id))
            created_count += 1

        document.status = LegalDocument.ProcessingStatus.EMBEDDING
        document.save(update_fields=["status", "updated_at"])

        duration = time.time() - start_time
        log.info("task_chunk_and_tag_complete", duration=duration, chunks=created_count)

        return {
            "document_id": document_id,
            "chunk_count": created_count,
        }

    except DocumentProcessingError:
        raise
    except Exception as exc:
        log.error("task_chunk_and_tag_failed", error=str(exc))
        try:
            from apps.documents.models import LegalDocument
            doc = _get_document(document_id)
            doc.status = LegalDocument.ProcessingStatus.FAILED
            doc.processing_error = str(exc)
            doc.save(update_fields=["status", "processing_error", "updated_at"])
        except Exception:
            pass
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_embed_and_index(self, document_id_or_result) -> dict:
    """
    Step 3: Embed chunks and index them in ChromaDB.

    1. Fetch un-embedded DocumentChunks
    2. Run EmbeddingService.embed_texts()
    3. Build VectorDocuments with lineage metadata
    4. Upsert into ChromaDB
    5. Mark chunks as embedded, set document READY
    """
    document_id = _extract_document_id(document_id_or_result)
    log = logger.bind(task_id=self.request.id, document_id=document_id)
    log.info("task_embed_and_index_start")
    start_time = time.time()

    try:
        from apps.documents.models import LegalDocument, DocumentChunk
        from apps.documents.services.embedding import EmbeddingService
        from apps.documents.services.lineage import generate_lineage
        from apps.documents.services.chunking import ChunkResult
        from apps.vector_store.repository import VectorRepository
        from apps.vector_store.schemas import VectorDocument
        from apps.vector_store.client import ChromaClientSingleton

        document = _get_document(document_id)
        chunks = DocumentChunk.objects.filter(
            document=document, is_embedded=False
        ).order_by("chunk_index")

        if not chunks.exists():
            log.warning("no_chunks_to_embed")
            document.status = LegalDocument.ProcessingStatus.READY
            document.save(update_fields=["status", "updated_at"])
            return {"document_id": document_id, "vectors_indexed": 0}

        # Collect texts for batch embedding
        chunk_list = list(chunks)
        texts = [c.chunk_text for c in chunk_list]

        embedding_service = EmbeddingService()
        embed_result = embedding_service.embed_texts(texts)

        # Build VectorDocuments
        vector_docs: list[VectorDocument] = []
        for i, db_chunk in enumerate(chunk_list):
            # Reconstruct ChunkResult for lineage generation
            chunk_result = ChunkResult(
                chunk_index=db_chunk.chunk_index,
                text=db_chunk.chunk_text,
                page_number=db_chunk.page_number,
                section_label=db_chunk.section_label,
                char_start=db_chunk.char_start,
                char_end=db_chunk.char_end,
                token_count=db_chunk.token_count,
            )

            lineage = generate_lineage(chunk_result, document, str(db_chunk.id))

            vector_docs.append(
                VectorDocument(
                    id=db_chunk.chroma_vector_id,
                    text=db_chunk.chunk_text,
                    embedding=embed_result.vectors[i],
                    metadata=lineage.to_dict(),
                )
            )

        # Upsert into ChromaDB
        repo = VectorRepository()
        upserted = repo.upsert_documents(str(document.session_id), vector_docs)

        # Mark chunks as embedded
        chunks.update(is_embedded=True)

        # Update document status
        collection_name = ChromaClientSingleton.collection_name(str(document.session_id))
        document.status = LegalDocument.ProcessingStatus.READY
        document.chroma_collection_name = collection_name
        document.save(update_fields=[
            "status", "chroma_collection_name", "updated_at"
        ])

        duration = time.time() - start_time
        log.info(
            "task_embed_and_index_complete",
            duration=duration,
            vectors_indexed=upserted,
            model=embed_result.model_used,
        )

        return {
            "document_id": document_id,
            "vectors_indexed": upserted,
        }

    except DocumentProcessingError:
        raise
    except Exception as exc:
        log.error("task_embed_and_index_failed", error=str(exc))
        try:
            from apps.documents.models import LegalDocument
            doc = _get_document(document_id)
            doc.status = LegalDocument.ProcessingStatus.FAILED
            doc.processing_error = str(exc)
            doc.save(update_fields=["status", "processing_error", "updated_at"])
        except Exception:
            pass
        raise self.retry(exc=exc)


def process_document_pipeline(document_id: str) -> AsyncResult:
    """
    Kick off the full document processing pipeline as a Celery chain.

    OCR → Chunk & Tag → Embed & Index

    Returns:
        AsyncResult with a task_id for status polling.
    """
    pipeline = chain(
        task_run_ocr.s(document_id),
        task_chunk_and_tag.s(),
        task_embed_and_index.s(),
    )
    return pipeline.apply_async()
