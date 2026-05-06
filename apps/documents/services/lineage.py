from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass


@dataclass
class LineageMetadata:
    document_id: str
    chunk_id: str
    chroma_vector_id: str
    session_id: str
    document_title: str
    document_type: str
    page_number: int | None
    section_label: str
    chunk_index: int
    char_start: int
    char_end: int
    text_hash: str
    token_count: int

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict) -> "LineageMetadata":
        return cls(
            document_id=value["document_id"],
            chunk_id=value["chunk_id"],
            chroma_vector_id=value["chroma_vector_id"],
            session_id=value["session_id"],
            document_title=value["document_title"],
            document_type=value["document_type"],
            page_number=value.get("page_number"),
            section_label=value.get("section_label", ""),
            chunk_index=value.get("chunk_index", 0),
            char_start=value.get("char_start", 0),
            char_end=value.get("char_end", 0),
            text_hash=value.get("text_hash", ""),
            token_count=value.get("token_count", 0),
        )


def generate_chroma_vector_id(document_id: str, chunk_index: int) -> str:
    return f"{document_id}:{chunk_index}"


def generate_text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_lineage(chunk, document, chunk_id: str) -> LineageMetadata:
    chroma_vector_id = getattr(
        chunk,
        "chroma_vector_id",
        generate_chroma_vector_id(str(document.id), chunk.chunk_index),
    )
    return LineageMetadata(
        document_id=str(document.id),
        chunk_id=str(chunk_id),
        chroma_vector_id=chroma_vector_id,
        session_id=str(document.session_id),
        document_title=document.title,
        document_type=document.document_type,
        page_number=getattr(chunk, "page_number", None),
        section_label=getattr(chunk, "section_label", "") or "",
        chunk_index=getattr(chunk, "chunk_index", 0),
        char_start=getattr(chunk, "char_start", 0),
        char_end=getattr(chunk, "char_end", 0),
        text_hash=getattr(chunk, "text_hash", generate_text_hash(chunk.text)),
        token_count=getattr(chunk, "token_count", len(chunk.text.split())),
    )
