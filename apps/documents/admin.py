"""
LexAI — Document Admin Registration
"""
from django.contrib import admin

from apps.documents.models import LegalDocument, DocumentChunk


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "document_type", "status", "session_id", "created_at")
    list_filter = ("status", "document_type")
    search_fields = ("title", "file_hash")
    readonly_fields = ("id", "file_hash", "file_size_bytes", "created_at", "updated_at")


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "section_label", "is_embedded", "token_count")
    list_filter = ("is_embedded",)
    search_fields = ("section_label", "text_hash")
    readonly_fields = ("id", "text_hash", "chroma_vector_id", "created_at")
