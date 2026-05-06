"""
Token budget per call:
  System prompt (cached after first call): ~400 tokens -> $0 after cache
  Chunks (capped at MAX_CHUNK_TOKENS_PER_CALL=2500): ~2500 tokens
  Query header: ~50 tokens
  Total input: ~2950 tokens -> $0.009 (Sonnet, cache miss) / $0.001 (cache hit)
  Output (capped at 1024): ~600 tokens -> $0.009
  Per synthesis call: ~$0.02 worst case, ~$0.01 typical
"""
from uuid import UUID, uuid4
from django.conf import settings
from pydantic import BaseModel
from .base import BaseAgent
from .schemas import SynthesisOutput, FactualClaim, RetrievedChunk
from apps.claude_client.client import get_claude


class _ClaimItem(BaseModel):
    claim_text: str
    source_vector_ids: list[str]
    confidence: float
    claim_type: str

class _SynthesisResponse(BaseModel):
    claims: list[_ClaimItem]
    narrative_summary: str


def _trim_chunks(chunks: list[RetrievedChunk], max_tokens: int) -> list[RetrievedChunk]:
    """Trim chunk list so total token estimate stays under max_tokens."""
    kept, total = [], 0
    for c in chunks:
        est = int(len(c.text.split()) * 1.35)
        if total + est > max_tokens:
            break
        kept.append(c)
        total += est
    return kept


def _format_chunks(chunks: list[RetrievedChunk]) -> str:
    lines = []
    for c in chunks:
        lines.append(
            f"[ID:{c.vector_id}][{c.document_title},p{c.page_number},{c.section_label}]\n{c.text}"
        )
    return "\n---\n".join(lines)


class SynthesisAgent(BaseAgent):
    agent_name = "Synthesis"

    def _execute(
        self,
        query_id: UUID,
        raw_query: str,
        rewritten_query: str,
        mode: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> SynthesisOutput:
        max_tok = settings.MAX_CHUNK_TOKENS_PER_CALL
        chunks = _trim_chunks(retrieved_chunks, max_tok)

        prompt_key = (
            "contradiction_detection"
            if mode == "CONTRADICTION_DETECT"
            else "pattern_extraction"
        )

        timeline_prefix = (
            "Reconstruct a chronological timeline. For each event: "
            "exact time/date if stated, location, persons, action. "
            "Flag ambiguous timings.\n\n"
            if mode == "TIMELINE_ANALYSIS" else ""
        )

        user_msg = (
            f"{timeline_prefix}"
            f"QUERY: {raw_query}\n\n"
            f"CONTEXT CHUNKS:\n{_format_chunks(chunks)}"
        )

        resp = get_claude().sonnet_json(prompt_key, user_msg, _SynthesisResponse)
        model_name = settings.CLAUDE_SONNET_MODEL

        claims = [
            FactualClaim(
                claim_id=uuid4(),
                claim_text=c.claim_text,
                source_vector_ids=c.source_vector_ids,
                confidence=c.confidence,
                claim_type=c.claim_type,
            )
            for c in resp.claims
        ]
        return SynthesisOutput(
            query_id=query_id,
            mode=mode,
            claims=claims,
            narrative_summary=resp.narrative_summary,
            claude_model_used=model_name,
            input_tokens=0,   # populated by ClaudeClient logger
            output_tokens=0,
        )
