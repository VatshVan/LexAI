"""
LexAI document serializers.
"""
from rest_framework import serializers

from apps.documents.models import DocumentChunk, LegalDocument


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)
    title = serializers.CharField(max_length=500, required=True)
    document_type = serializers.ChoiceField(
        choices=LegalDocument.DocumentType.choices,
        default=LegalDocument.DocumentType.OTHER,
    )
    session_id = serializers.UUIDField(required=False, allow_null=True)


class DocumentStatusSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(source="id", read_only=True)
    title = serializers.CharField(read_only=True)
    chunk_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = LegalDocument
        fields = [
            "document_id",
            "title",
            "status",
            "page_count",
            "chunk_count",
            "processing_error",
        ]


class DocumentDetailSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(source="id", read_only=True)
    chunk_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = LegalDocument
        fields = [
            "document_id",
            "title",
            "document_type",
            "file",
            "file_hash",
            "file_size_bytes",
            "mime_type",
            "page_count",
            "status",
            "ocr_engine_used",
            "processing_error",
            "session_id",
            "chroma_collection_name",
            "chunk_count",
            "created_at",
            "updated_at",
        ]


class SessionDocumentSerializer(serializers.ModelSerializer):
    document_id = serializers.UUIDField(source="id", read_only=True)
    chunk_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = LegalDocument
        fields = [
            "document_id",
            "title",
            "document_type",
            "status",
            "page_count",
            "file_size_bytes",
            "chunk_count",
            "created_at",
        ]
