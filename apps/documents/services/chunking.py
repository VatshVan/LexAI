"""
LexAI — Legal-Boundary-Aware Document Chunker

Hierarchical, rule-based chunker optimized for legal documents.
NOT a naive character/word count chunker.

Chunking strategy (priority order):
1. STRUCTURAL BOUNDARIES — legal section markers (WHEREAS, Section X, Clause X.X)
2. PARAGRAPH BOUNDARIES — double newlines within oversized sections
3. SENTENCE BOUNDARIES — regex-based sentence splitting (fallback)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import structlog

from apps.core.exceptions import ChunkingError
from infrastructure.ocr.base import OCRResult

logger = structlog.get_logger(__name__)

# ─── Configuration ─────────────────────────────────────
DEFAULT_MAX_CHUNK_TOKENS = 512
DEFAULT_MIN_CHUNK_TOKENS = 50
DEFAULT_OVERLAP_TOKENS = 50

# ─── Legal Section Markers (regex patterns) ────────────
STRUCTURAL_PATTERNS = [
    # Legal preamble markers
    (r"(?:^|\n)\s*(WHEREAS\b)", "WHEREAS"),
    (r"(?:^|\n)\s*(WHEREFORE\b)", "WHEREFORE"),
    (r"(?:^|\n)\s*(NOW\s+THEREFORE\b)", "NOW THEREFORE"),
    # Numbered sections and clauses
    (r"(?:^|\n)\s*(Section\s+\d+[\.\d]*)", None),
    (r"(?:^|\n)\s*(SECTION\s+\d+[\.\d]*)", None),
    (r"(?:^|\n)\s*(Clause\s+\d+[\.\d]*)", None),
    (r"(?:^|\n)\s*(Article\s+\d+[\.\d]*)", None),
    # Document-specific markers
    (r"(?:^|\n)\s*(Witness\s+Statement\s+of\s+[A-Z][a-zA-Z\s]+)", None),
    (r"(?:^|\n)\s*(Exhibit\s+[A-Z0-9]+)", None),
    (r"(?:^|\n)\s*(FIR\s+No\.\s*[\d/]+)", None),
    (r"(?:^|\n)\s*(Page\s+\d+\s+of\s+\d+)", None),
    # Common legal headings
    (r"(?:^|\n)\s*(SCHEDULE\s+[A-Z0-9]*)", None),
    (r"(?:^|\n)\s*(ANNEXURE\s+[A-Z0-9]*)", None),
    (r"(?:^|\n)\s*(PRAYER\b)", "PRAYER"),
    (r"(?:^|\n)\s*(ORDER\b)", "ORDER"),
    (r"(?:^|\n)\s*(RELIEF\s+SOUGHT)", "RELIEF SOUGHT"),
]

# Compile patterns once
_COMPILED_PATTERNS = [
    (re.compile(pattern, re.IGNORECASE | re.MULTILINE), label)
    for pattern, label in STRUCTURAL_PATTERNS
]

# Sentence boundary regex (handles abbreviations common in legal text)
_SENTENCE_BOUNDARY = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])"
)


@dataclass
class ChunkResult:
    """A single chunk produced by the legal chunker."""

    chunk_index: int
    text: str
    page_number: int | None
    section_label: str
    char_start: int
    char_end: int
    token_count: int


def _count_tokens(text: str) -> int:
    """Simple whitespace tokenizer for approximate token counting."""
    return len(text.split())


def _find_page_for_offset(page_offsets: list[tuple[int, int, int]], char_start: int) -> int | None:
    """
    Given a list of (page_num, start_offset, end_offset) tuples,
    find which page contains the given character offset.
    """
    for page_num, start, end in page_offsets:
        if start <= char_start < end:
            return page_num
    return None


class LegalDocumentChunker:
    """
    Hierarchical, rule-based legal document chunker.

    Splits documents respecting:
    1. Structural legal boundaries (highest priority)
    2. Paragraph boundaries (medium priority)
    3. Sentence boundaries with overlap (fallback)
    """

    def __init__(
        self,
        max_chunk_tokens: int = DEFAULT_MAX_CHUNK_TOKENS,
        min_chunk_tokens: int = DEFAULT_MIN_CHUNK_TOKENS,
        overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
    ):
        self.max_chunk_tokens = max_chunk_tokens
        self.min_chunk_tokens = min_chunk_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, ocr_result: OCRResult) -> list[ChunkResult]:
        """
        Chunk an OCR result into semantically coherent pieces.

        Args:
            ocr_result: The OCR result containing raw text and page data.

        Returns:
            Ordered list of ChunkResult.

        Raises:
            ChunkingError: If chunking fails.
        """
        logger.info(
            "chunking_start",
            char_count=len(ocr_result.raw_text),
            page_count=ocr_result.page_count,
        )

        if not ocr_result.raw_text.strip():
            logger.warning("chunking_empty_text")
            return []

        try:
            # Build page offset map for page number tracking
            page_offsets = self._build_page_offsets(ocr_result)

            # Step 1: Split on structural boundaries
            sections = self._split_structural(ocr_result.raw_text)

            # Step 2 & 3: Sub-split oversized sections
            raw_chunks: list[dict] = []
            for section in sections:
                text = section["text"]
                token_count = _count_tokens(text)

                if token_count <= self.max_chunk_tokens:
                    raw_chunks.append(section)
                else:
                    # Split on paragraphs first, then sentences
                    sub_chunks = self._split_paragraphs(
                        text, section["label"], section["char_start"]
                    )
                    raw_chunks.extend(sub_chunks)

            # Step 4: Merge micro-chunks and assign page numbers
            chunks = self._merge_and_finalize(raw_chunks, page_offsets)

            logger.info("chunking_complete", chunk_count=len(chunks))
            return chunks

        except ChunkingError:
            raise
        except Exception as e:
            logger.error("chunking_failed", error=str(e))
            raise ChunkingError(
                message="Document chunking failed",
                detail=str(e),
            )

    def _build_page_offsets(self, ocr_result: OCRResult) -> list[tuple[int, int, int]]:
        """Build a map of (page_number, char_start, char_end) from OCR page texts."""
        offsets = []
        current_offset = 0
        for i, page_text in enumerate(ocr_result.page_texts):
            start = current_offset
            end = start + len(page_text)
            offsets.append((i + 1, start, end))  # 1-indexed pages
            current_offset = end + 2  # Account for \n\n separator
        return offsets

    def _split_structural(self, text: str) -> list[dict]:
        """
        Split text on structural legal boundaries.
        Returns list of dicts with text, label, and char_start.
        """
        # Find all structural boundary positions
        boundaries: list[tuple[int, str]] = []

        for pattern, default_label in _COMPILED_PATTERNS:
            for match in pattern.finditer(text):
                label = default_label or match.group(1).strip()
                boundaries.append((match.start(), label))

        if not boundaries:
            # No structural boundaries found — treat entire text as one section
            return [{"text": text, "label": "", "char_start": 0}]

        # Sort by position
        boundaries.sort(key=lambda x: x[0])

        # Deduplicate boundaries that are very close together (within 10 chars)
        deduped: list[tuple[int, str]] = [boundaries[0]]
        for pos, label in boundaries[1:]:
            if pos - deduped[-1][0] > 10:
                deduped.append((pos, label))

        # Create sections from boundaries
        sections: list[dict] = []

        # Text before first boundary
        if deduped[0][0] > 0:
            pre_text = text[: deduped[0][0]].strip()
            if pre_text:
                sections.append({
                    "text": pre_text,
                    "label": "Preamble",
                    "char_start": 0,
                })

        # Sections between boundaries
        for i, (pos, label) in enumerate(deduped):
            end = deduped[i + 1][0] if i + 1 < len(deduped) else len(text)
            section_text = text[pos:end].strip()
            if section_text:
                sections.append({
                    "text": section_text,
                    "label": label,
                    "char_start": pos,
                })

        return sections if sections else [{"text": text, "label": "", "char_start": 0}]

    def _split_paragraphs(
        self, text: str, parent_label: str, base_offset: int
    ) -> list[dict]:
        """
        Split an oversized section on paragraph boundaries (double newlines).
        Falls back to sentence splitting if paragraphs are still too large.
        """
        paragraphs = re.split(r"\n\s*\n", text)
        chunks: list[dict] = []
        current_offset = 0

        for para_idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                current_offset += 2  # skip empty paragraph
                continue

            para_tokens = _count_tokens(para)
            # Build sub-label
            sub_label = f"{parent_label} [¶{para_idx + 1}]" if parent_label else f"¶{para_idx + 1}"

            # Find actual offset of this paragraph in original text
            try:
                para_start = text.index(para, current_offset)
            except ValueError:
                para_start = current_offset

            if para_tokens <= self.max_chunk_tokens:
                chunks.append({
                    "text": para,
                    "label": sub_label,
                    "char_start": base_offset + para_start,
                })
            else:
                # Sentence-level splitting with overlap
                sentence_chunks = self._split_sentences(
                    para, sub_label, base_offset + para_start
                )
                chunks.extend(sentence_chunks)

            current_offset = para_start + len(para)

        return chunks

    def _split_sentences(
        self, text: str, parent_label: str, base_offset: int
    ) -> list[dict]:
        """
        Split an oversized paragraph on sentence boundaries with overlap.
        """
        sentences = _SENTENCE_BOUNDARY.split(text)
        if len(sentences) <= 1:
            # Can't split further — return as-is even if oversized
            return [{"text": text, "label": parent_label, "char_start": base_offset}]

        chunks: list[dict] = []
        current_sentences: list[str] = []
        current_tokens = 0
        chunk_start_offset = 0

        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence:
                continue

            sent_tokens = _count_tokens(sentence)

            if current_tokens + sent_tokens > self.max_chunk_tokens and current_sentences:
                # Emit current chunk
                chunk_text = " ".join(current_sentences)
                try:
                    actual_start = text.index(current_sentences[0], chunk_start_offset)
                except ValueError:
                    actual_start = chunk_start_offset

                chunks.append({
                    "text": chunk_text,
                    "label": parent_label,
                    "char_start": base_offset + actual_start,
                })

                # Apply overlap: keep last N tokens worth of sentences
                overlap_sentences: list[str] = []
                overlap_tokens = 0
                for s in reversed(current_sentences):
                    s_tokens = _count_tokens(s)
                    if overlap_tokens + s_tokens > self.overlap_tokens:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_tokens += s_tokens

                current_sentences = overlap_sentences
                current_tokens = overlap_tokens
                chunk_start_offset = actual_start + len(chunk_text)

            current_sentences.append(sentence)
            current_tokens += sent_tokens

        # Emit final chunk
        if current_sentences:
            chunk_text = " ".join(current_sentences)
            try:
                actual_start = text.index(current_sentences[0], chunk_start_offset)
            except ValueError:
                actual_start = chunk_start_offset

            chunks.append({
                "text": chunk_text,
                "label": parent_label,
                "char_start": base_offset + actual_start,
            })

        return chunks

    def _merge_and_finalize(
        self, raw_chunks: list[dict], page_offsets: list[tuple[int, int, int]]
    ) -> list[ChunkResult]:
        """
        Merge micro-chunks (below MIN_CHUNK_TOKENS) and assign final metadata.
        """
        if not raw_chunks:
            return []

        # Merge micro-chunks with previous chunk
        merged: list[dict] = []
        for chunk in raw_chunks:
            token_count = _count_tokens(chunk["text"])

            if token_count < self.min_chunk_tokens and merged:
                # Merge with previous chunk
                prev = merged[-1]
                prev["text"] = prev["text"] + "\n\n" + chunk["text"]
                prev["token_count"] = _count_tokens(prev["text"])
            else:
                chunk["token_count"] = token_count
                merged.append(chunk)

        # Build final ChunkResult list
        results: list[ChunkResult] = []
        for idx, chunk in enumerate(merged):
            char_start = chunk["char_start"]
            char_end = char_start + len(chunk["text"])
            page_number = _find_page_for_offset(page_offsets, char_start)

            results.append(
                ChunkResult(
                    chunk_index=idx,
                    text=chunk["text"],
                    page_number=page_number,
                    section_label=chunk.get("label", ""),
                    char_start=char_start,
                    char_end=char_end,
                    token_count=chunk.get("token_count", _count_tokens(chunk["text"])),
                )
            )

        return results
