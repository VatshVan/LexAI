import os
import json

files = {
    'apps/agents/__init__.py': '',
    
    'apps/agents/schemas.py': '''from pydantic import BaseModel, Field
from enum import Enum
from uuid import UUID, uuid4
from typing import Literal

class QueryIntent(str, Enum):
    PATTERN_EXTRACTION   = "PATTERN_EXTRACTION"
    CONTRADICTION_DETECT = "CONTRADICTION_DETECT"
    TIMELINE_ANALYSIS    = "TIMELINE_ANALYSIS"
    DRAFT_BAIL_PETITION  = "DRAFT_BAIL_PETITION"
    DRAFT_LEGAL_NOTICE   = "DRAFT_LEGAL_NOTICE"
    DRAFT_ANTICIPATORY   = "DRAFT_ANTICIPATORY_BAIL"
    DRAFT_VAKALATNAMA    = "DRAFT_VAKALATNAMA"
    FACTUAL_QUERY        = "FACTUAL_QUERY"
    UNSUPPORTED          = "UNSUPPORTED"

DRAFT_INTENTS = {
    QueryIntent.DRAFT_BAIL_PETITION,
    QueryIntent.DRAFT_LEGAL_NOTICE,
    QueryIntent.DRAFT_ANTICIPATORY,
    QueryIntent.DRAFT_VAKALATNAMA,
}

INTENT_TO_TEMPLATE = {
    QueryIntent.DRAFT_BAIL_PETITION: "bail_petition",
    QueryIntent.DRAFT_LEGAL_NOTICE:  "legal_notice",
    QueryIntent.DRAFT_ANTICIPATORY:  "anticipatory_bail",
    QueryIntent.DRAFT_VAKALATNAMA:   "vakalatnama",
}

class IntentClassificationOutput(BaseModel):
    query_id: UUID
    intent: QueryIntent
    rewritten_query: str
    target_document_types: list[str]
    confidence: float
    reasoning: str

class RetrievedChunk(BaseModel):
    vector_id: str
    text: str
    relevance_score: float
    page_number: int | None
    section_label: str
    document_id: str
    document_title: str
    document_type: str
    chunk_index: int
    text_hash: str

class RetrievalOutput(BaseModel):
    query_id: UUID
    retrieved_chunks: list[RetrievedChunk]
    total_retrieved: int
    retrieval_strategy: str   # "filtered" | "broad" | "expanded"

class FactualClaim(BaseModel):
    claim_id: UUID = Field(default_factory=uuid4)
    claim_text: str
    source_vector_ids: list[str]
    confidence: float
    claim_type: str
    is_verified: bool = False
    verification_score: float | None = None
    is_flagged: bool = False

class SynthesisOutput(BaseModel):
    query_id: UUID
    mode: str
    claims: list[FactualClaim]
    narrative_summary: str
    claude_model_used: str
    input_tokens: int
    output_tokens: int

class TemplateVariable(BaseModel):
    field_name: str
    field_value: str | None
    source_vector_ids: list[str]
    is_null: bool
    requires_lawyer_review: bool = True

class DraftingOutput(BaseModel):
    query_id: UUID
    template_name: str
    template_variables: list[TemplateVariable]
    null_field_count: int
    filled_field_count: int
    draft_html: str
    draft_raw: dict
    claims: list[FactualClaim]

class AgentStatus(str, Enum):
    PENDING  = "PENDING"
    RUNNING  = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED   = "FAILED"
    SKIPPED  = "SKIPPED"

class AgentExecutionRecord(BaseModel):
    agent_name: str
    status: AgentStatus
    started_at: str | None = None
    completed_at: str | None = None
    duration_ms: int | None = None
    error: str | None = None

class QueryResult(BaseModel):
    query_id: UUID
    session_id: UUID
    raw_query: str
    intent: QueryIntent
    status: AgentStatus
    execution_trace: list[AgentExecutionRecord]
    result_payload: SynthesisOutput | DraftingOutput | None
    verification_report: dict | None = None
    created_at: str
    completed_at: str | None = None
''',
    
    'apps/claude_client/__init__.py': '',
    
    'apps/claude_client/client.py': '''"""
TOKEN-OPTIMIZED CLAUDE CLIENT

Cost controls enforced here:
1. Model tiering: Haiku for cheap tasks, Sonnet for complex reasoning
2. Prompt caching: system prompts cached 1h (10x cost reduction on cache hits)
3. Output cap: Haiku<=512, Sonnet<=1024 tokens
4. Context trimming: caller must pre-trim chunks to MAX_CHUNK_TOKENS_PER_CALL

Rate limit guard:
  5 req/min across ALL models. If pipeline fires agents concurrently, we hit
  this limit. Solution: pipeline is sequential (one agent at a time).
  ClaudeClient adds 0.5s sleep after each call as a soft rate guard.
"""

import anthropic
import json
import time
import structlog
from pathlib import Path
from django.conf import settings
from pydantic import BaseModel

log = structlog.get_logger()
PROMPTS_DIR = Path(__file__).parent / "prompts"


class ClaudeClient:
    _instance = None
    _client: anthropic.Anthropic = None
    _prompts: dict[str, str] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
            cls._instance._prompts = {
                p.stem: p.read_text()
                for p in PROMPTS_DIR.glob("*.txt")
            }
            log.info("claude_client_ready",
                     prompts_loaded=list(cls._instance._prompts.keys()))
        return cls._instance

    def _call(
        self,
        system_key: str,
        user_message: str,
        model: str,
        max_tokens: int,
    ) -> anthropic.types.Message:
        """
        Raw call with prompt caching on system prompt.
        Retries 3x on 429/529 with exponential backoff.
        Sleeps 0.5s after every successful call (rate limit guard).
        """
        system_text = self._prompts[system_key]
        attempt = 0
        while attempt < settings.CLAUDE_MAX_RETRIES:
            try:
                response = self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=settings.CLAUDE_TEMPERATURE,
                    system=[{
                        "type": "text",
                        "text": system_text,
                        "cache_control": {"type": "ephemeral"},  # 1h cache
                    }],
                    messages=[{"role": "user", "content": user_message}],
                )
                log.info("claude_call_success",
                         model=model, system_key=system_key,
                         input_tokens=response.usage.input_tokens,
                         output_tokens=response.usage.output_tokens,
                         cache_read=getattr(response.usage,
                                            "cache_read_input_tokens", 0))
                time.sleep(0.5)  # soft rate guard
                return response
            except anthropic.RateLimitError:
                wait = 2 ** attempt * 12  # 12s, 24s, 48s
                log.warning("claude_rate_limit", wait_seconds=wait)
                time.sleep(wait)
                attempt += 1
            except anthropic.OverloadedError:
                wait = 2 ** attempt * 6
                log.warning("claude_overloaded", wait_seconds=wait)
                time.sleep(wait)
                attempt += 1
        raise Exception(f"Claude call failed after {settings.CLAUDE_MAX_RETRIES} retries")

    def haiku(self, system_key: str, user_message: str) -> str:
        """Cheap call — intent, decomposition, simple tasks."""
        resp = self._call(system_key, user_message,
                          settings.CLAUDE_HAIKU_MODEL,
                          settings.CLAUDE_HAIKU_MAX_TOKENS)
        return resp.content[0].text

    def sonnet(self, system_key: str, user_message: str) -> str:
        """Powerful call — synthesis, contradiction, drafting."""
        resp = self._call(system_key, user_message,
                          settings.CLAUDE_SONNET_MODEL,
                          settings.CLAUDE_SONNET_MAX_TOKENS)
        return resp.content[0].text

    def haiku_json(self, system_key: str, user_message: str,
                   schema: type[BaseModel]) -> BaseModel:
        raw = self.haiku(system_key, user_message)
        return self._parse_json(raw, schema)

    def sonnet_json(self, system_key: str, user_message: str,
                    schema: type[BaseModel]) -> BaseModel:
        raw = self.sonnet(system_key, user_message)
        return self._parse_json(raw, schema)

    def _parse_json(self, raw: str, schema: type[BaseModel]) -> BaseModel:
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            return schema.model_validate(json.loads(clean))
        except Exception as e:
            log.error("claude_json_parse_failed", raw=raw[:200], error=str(e))
            raise


def get_claude() -> ClaudeClient:
    return ClaudeClient()
''',
    
    'apps/claude_client/prompts/intent_classification.txt': '''You classify Indian lawyer queries into structured intents. Be concise.

INTENTS: PATTERN_EXTRACTION | CONTRADICTION_DETECT | TIMELINE_ANALYSIS |
DRAFT_BAIL_PETITION | DRAFT_LEGAL_NOTICE | DRAFT_ANTICIPATORY_BAIL |
DRAFT_VAKALATNAMA | FACTUAL_QUERY | UNSUPPORTED

RULES:
- "inconsistency/contradiction/conflict/differ" -> CONTRADICTION_DETECT
- "timeline/sequence/when/order of events" -> TIMELINE_ANALYSIS
- "draft/write/prepare/petition/notice" -> appropriate DRAFT_*
- Rewrite query to be more precise for semantic vector search
- target_document_types: subset of [FIR, AFFIDAVIT, WITNESS_STATEMENT,
  BAIL_APPLICATION, LEGAL_NOTICE, OTHER]

Respond ONLY with valid JSON, no explanation:
{"intent":"...","rewritten_query":"...","target_document_types":["..."],
"confidence":0.0,"reasoning":"one sentence"}
''',
    
    'apps/claude_client/prompts/pattern_extraction.txt': '''You are an Indian legal analyst. Extract facts from provided document chunks ONLY.
Never use outside knowledge. Every claim must cite its source chunk ID.

OUTPUT RULES:
- claims: 3-8 atomic facts maximum (do not pad)
- Each claim: one discrete fact, traceable to exactly one chunk
- narrative_summary: 2-3 sentences maximum
- claim_type: "timeline_fact"|"witness_fact"|"physical_evidence"|"procedural_fact"

Respond ONLY with valid JSON:
{"claims":[{"claim_text":"...","source_vector_ids":["..."],"confidence":0.0,
"claim_type":"..."}],"narrative_summary":"..."}
''',
    
    'apps/claude_client/prompts/contradiction_detection.txt': '''You are a forensic Indian legal analyst finding contradictions between documents.
Compare ONLY the provided chunks. Never infer beyond what is stated.

CONTRADICTION TYPES: timeline | spatial | identity | sequence | omission

OUTPUT RULES:
- claims: list contradictions only (empty array if none found — do not fabricate)
- Each contradiction claim MUST reference >=2 source_vector_ids (the conflicting chunks)
- claim_text: "[Source A] states X, but [Source B] states Y" format
- claim_type: always "contradiction"

Respond ONLY with valid JSON:
{"claims":[{"claim_text":"...","source_vector_ids":["...","..."],
"confidence":0.0,"claim_type":"contradiction"}],"narrative_summary":"..."}
''',
    
    'apps/claude_client/prompts/template_extraction.txt': '''You extract values from legal documents to fill a template. Use ONLY the
provided context. If a value is not explicitly present, output "NULL".
Never fabricate names, dates, numbers, or legal references.

EXTRACTION RULES:
- field_value: exact text from source, or "NULL" if not found
- is_null: true when field_value is "NULL"
- source_vector_ids: which chunk(s) provided the value

Respond ONLY with valid JSON:
{"extracted_fields":[{"field_name":"...","field_value":"...or NULL",
"source_vector_ids":["..."],"is_null":false}]}
''',
    
    'apps/claude_client/prompts/query_rewriting.txt': '''Expand this Indian legal search query with synonyms and alternative phrasings.
Include: accused/defendant/respondent variants, Indian legal terminology,
IPC/CrPC section names if applicable.
Return ONLY the expanded query string. No JSON. No explanation.
''',
    
    'apps/agents/base.py': '''from abc import ABC, abstractmethod
from time import perf_counter
import structlog
from pydantic import BaseModel

log = structlog.get_logger()


class AgentExecutionError(Exception):
    def __init__(self, agent: str, cause: Exception):
        self.agent = agent
        self.cause = cause
        super().__init__(f"Agent '{agent}' failed: {cause}")


class BaseAgent(ABC):
    agent_name: str = "BaseAgent"

    def execute(self, *args, **kwargs):
        start = perf_counter()
        bound = log.bind(agent=self.agent_name)
        bound.info("agent_start")
        try:
            result = self._execute(*args, **kwargs)
            bound.info("agent_complete",
                       duration_ms=int((perf_counter() - start) * 1000))
            return result
        except AgentExecutionError:
            raise
        except Exception as e:
            bound.error("agent_failed", error=str(e))
            raise AgentExecutionError(self.agent_name, e)

    @abstractmethod
    def _execute(self, *args, **kwargs):
        ...
''',

    'apps/agents/intent_classifier.py': '''from uuid import UUID
from pydantic import BaseModel
from .base import BaseAgent
from .schemas import IntentClassificationOutput, QueryIntent
from apps.claude_client.client import get_claude


class _ClaudeIntentResponse(BaseModel):
    intent: str
    rewritten_query: str
    target_document_types: list[str]
    confidence: float
    reasoning: str


class IntentClassifierAgent(BaseAgent):
    agent_name = "IntentClassifier"

    def _execute(
        self,
        query_id: UUID,
        session_id: UUID,
        raw_query: str,
        available_document_types: list[str],
    ) -> IntentClassificationOutput:
        user_msg = (
            f"QUERY: {raw_query}\\n"
            f"AVAILABLE_DOC_TYPES: {', '.join(available_document_types)}"
        )
        resp = get_claude().haiku_json(
            "intent_classification", user_msg, _ClaudeIntentResponse
        )
        intent = QueryIntent(resp.intent) if resp.intent in QueryIntent._value2member_map_ \\
            else QueryIntent.FACTUAL_QUERY
        if resp.confidence < 0.5:
            intent = QueryIntent.FACTUAL_QUERY
        return IntentClassificationOutput(
            query_id=query_id,
            intent=intent,
            rewritten_query=resp.rewritten_query,
            target_document_types=resp.target_document_types,
            confidence=resp.confidence,
            reasoning=resp.reasoning,
        )
''',

    'apps/agents/retrieval_agent.py': '''from uuid import UUID
from django.conf import settings
from .base import BaseAgent
from .schemas import RetrievalOutput, RetrievedChunk
from apps.documents.services.embedding import EmbeddingService
from apps.vector_store.repository import VectorRepository
from apps.vector_store.schemas import SearchResult
from apps.documents.services.lineage import LineageMetadata
from apps.claude_client.client import get_claude
import structlog

log = structlog.get_logger()


class RetrievalAgent(BaseAgent):
    agent_name = "Retrieval"

    def _execute(
        self,
        session_id: UUID,
        query_id: UUID,
        rewritten_query: str,
        target_document_types: list[str],
        top_k: int = None,
        min_score: float = None,
    ) -> RetrievalOutput:
        top_k = top_k or settings.DEFAULT_TOP_K
        min_score = min_score or settings.MIN_RELEVANCE_SCORE
        embedding = EmbeddingService().embed_query(rewritten_query)
        repo = VectorRepository()

        # Strategy A: filtered
        results = repo.semantic_search(
            session_id=str(session_id),
            query_embedding=embedding,
            top_k=top_k,
            filter_metadata={"document_type": {"$in": target_document_types}}
            if target_document_types else None,
        )
        strategy = "filtered"

        # Strategy B: broad fallback
        if len(results) < 3:
            results = repo.semantic_search(
                session_id=str(session_id),
                query_embedding=embedding,
                top_k=top_k,
            )
            strategy = "broad"

        # Strategy C: query expansion
        if len(results) < 3:
            expanded = get_claude().haiku("query_rewriting", rewritten_query)
            embedding2 = EmbeddingService().embed_query(expanded.strip())
            results = repo.semantic_search(
                session_id=str(session_id),
                query_embedding=embedding2,
                top_k=top_k,
            )
            strategy = "expanded"

        filtered = [r for r in results if r.relevance_score >= min_score]
        chunks = [self._to_chunk(r) for r in filtered]
        return RetrievalOutput(
            query_id=query_id,
            retrieved_chunks=chunks,
            total_retrieved=len(chunks),
            retrieval_strategy=strategy,
        )

    def _to_chunk(self, r: SearchResult) -> RetrievedChunk:
        m = r.metadata
        return RetrievedChunk(
            vector_id=r.id,
            text=r.text,
            relevance_score=r.relevance_score,
            page_number=m.page_number if isinstance(m, LineageMetadata) else m.get("page_number"),
            section_label=m.section_label if isinstance(m, LineageMetadata) else m.get("section_label", ""),
            document_id=m.document_id if isinstance(m, LineageMetadata) else m.get("document_id", ""),
            document_title=m.document_title if isinstance(m, LineageMetadata) else m.get("document_title", ""),
            document_type=m.document_type if isinstance(m, LineageMetadata) else m.get("document_type", ""),
            chunk_index=m.chunk_index if isinstance(m, LineageMetadata) else m.get("chunk_index", 0),
            text_hash=m.text_hash if isinstance(m, LineageMetadata) else m.get("text_hash", ""),
        )
''',

    'apps/agents/synthesis_agent.py': '''"""
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
            f"[ID:{c.vector_id}][{c.document_title},p{c.page_number},{c.section_label}]\\n{c.text}"
        )
    return "\\n---\\n".join(lines)


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
            "Flag ambiguous timings.\\n\\n"
            if mode == "TIMELINE_ANALYSIS" else ""
        )

        user_msg = (
            f"{timeline_prefix}"
            f"QUERY: {raw_query}\\n\\n"
            f"CONTEXT CHUNKS:\\n{_format_chunks(chunks)}"
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
''',

    'apps/agents/drafting_agent.py': '''from uuid import UUID, uuid4
from django.conf import settings
from pydantic import BaseModel
from .base import BaseAgent
from .schemas import DraftingOutput, TemplateVariable, FactualClaim, RetrievedChunk
from apps.claude_client.client import get_claude
from apps.templates_engine.registry import TemplateRegistry
from apps.templates_engine.renderer import TemplateRenderer
from .synthesis_agent import _trim_chunks, _format_chunks


class _ExtractedField(BaseModel):
    field_name: str
    field_value: str | None
    source_vector_ids: list[str]
    is_null: bool

class _ExtractionResponse(BaseModel):
    extracted_fields: list[_ExtractedField]


class DraftingAgent(BaseAgent):
    agent_name = "Drafting"

    def _execute(
        self,
        query_id: UUID,
        session_id: UUID,
        template_name: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> DraftingOutput:
        template = TemplateRegistry().get_template(template_name)
        chunks = _trim_chunks(retrieved_chunks, settings.MAX_CHUNK_TOKENS_PER_CALL)

        user_msg = (
            f"TEMPLATE FIELDS:\\n{[f['field_name']+': '+f['description'] for f in template['fields']]}\\n\\n"
            f"CONTEXT CHUNKS:\\n{_format_chunks(chunks)}"
        )
        resp = get_claude().sonnet_json("template_extraction", user_msg, _ExtractionResponse)

        variables = [
            TemplateVariable(
                field_name=f.field_name,
                field_value=None if f.is_null else f.field_value,
                source_vector_ids=f.source_vector_ids,
                is_null=f.is_null,
            )
            for f in resp.extracted_fields
        ]
        null_count = sum(1 for v in variables if v.is_null)
        filled_count = len(variables) - null_count
        draft_html = TemplateRenderer().render(template, variables)

        # Convert to FactualClaims for Part 3 verification
        claims = [
            FactualClaim(
                claim_id=uuid4(),
                claim_text=f"{v.field_name}: {v.field_value}",
                source_vector_ids=v.source_vector_ids,
                confidence=0.9,
                claim_type="template_extraction",
            )
            for v in variables if not v.is_null
        ]
        return DraftingOutput(
            query_id=query_id,
            template_name=template_name,
            template_variables=variables,
            null_field_count=null_count,
            filled_field_count=filled_count,
            draft_html=draft_html,
            draft_raw={"template": template, "variables": [v.model_dump() for v in variables]},
            claims=claims,
        )
''',

    'apps/templates_engine/templates/bail_petition.json': '''{
  "template_name": "bail_petition",
  "display_name": "Bail Petition",
  "version": "1.0",
  "fields": [
    {"field_name": "court_name", "description": "Full name of the court", "required": true},
    {"field_name": "case_number", "description": "Case registration number", "required": true},
    {"field_name": "fir_number", "description": "FIR number including year and police station", "required": true},
    {"field_name": "fir_date", "description": "Date of FIR registration (DD/MM/YYYY)", "required": true},
    {"field_name": "police_station", "description": "Name of police station that registered FIR", "required": true},
    {"field_name": "accused_name", "description": "Full legal name of the accused", "required": true},
    {"field_name": "accused_age", "description": "Age of accused in years", "required": true},
    {"field_name": "accused_address", "description": "Complete residential address of accused", "required": true},
    {"field_name": "sections_of_law", "description": "IPC/CrPC sections accused is charged under", "required": true},
    {"field_name": "grounds_for_bail", "description": "Primary grounds for bail grant", "required": true},
    {"field_name": "surety_name", "description": "Full name of surety/guarantor", "required": false},
    {"field_name": "surety_address", "description": "Complete address of surety", "required": false},
    {"field_name": "advocate_name", "description": "Name of the filing advocate", "required": true},
    {"field_name": "date_of_application", "description": "Date of this petition (DD/MM/YYYY)", "required": true}
  ]
}''',

    'apps/templates_engine/templates/legal_notice.json': '''{
  "template_name": "legal_notice",
  "display_name": "Legal Notice",
  "version": "1.0",
  "fields": [
    {"field_name": "sender_name", "description": "Full name of notice sender", "required": true},
    {"field_name": "sender_address", "description": "Complete address of sender", "required": true},
    {"field_name": "recipient_name", "description": "Full name of notice recipient", "required": true},
    {"field_name": "recipient_address", "description": "Complete address of recipient", "required": true},
    {"field_name": "subject_of_notice", "description": "Brief subject line of the notice", "required": true},
    {"field_name": "facts_of_case", "description": "Chronological facts leading to notice", "required": true},
    {"field_name": "legal_demand", "description": "Specific demand being made", "required": true},
    {"field_name": "time_limit_days", "description": "Days given to comply (typically 15 or 30)", "required": true},
    {"field_name": "consequences_of_non_compliance", "description": "Legal action if demand not met", "required": true},
    {"field_name": "advocate_name", "description": "Name of advocate sending notice", "required": true},
    {"field_name": "notice_date", "description": "Date of notice (DD/MM/YYYY)", "required": true}
  ]
}''',

    'apps/templates_engine/templates/anticipatory_bail.json': '''{
  "template_name": "anticipatory_bail",
  "display_name": "Anticipatory Bail Application",
  "version": "1.0",
  "fields": [
    {"field_name": "court_name", "description": "Sessions Court or High Court name", "required": true},
    {"field_name": "applicant_name", "description": "Name of applicant seeking anticipatory bail", "required": true},
    {"field_name": "applicant_address", "description": "Complete address of applicant", "required": true},
    {"field_name": "sections_of_law", "description": "Sections applicant apprehends arrest under", "required": true},
    {"field_name": "apprehension_grounds", "description": "Reason applicant fears arrest", "required": true},
    {"field_name": "fir_number", "description": "FIR number if already registered", "required": false},
    {"field_name": "police_station", "description": "Police station where FIR registered", "required": false},
    {"field_name": "proposed_conditions", "description": "Conditions applicant agrees to comply with", "required": false},
    {"field_name": "prior_anticipatory_applications", "description": "Previous AB applications if any", "required": false},
    {"field_name": "advocate_name", "description": "Name of filing advocate", "required": true},
    {"field_name": "date_of_application", "description": "Date of filing (DD/MM/YYYY)", "required": true}
  ]
}''',

    'apps/templates_engine/templates/vakalatnama.json': '''{
  "template_name": "vakalatnama",
  "display_name": "Vakalatnama",
  "version": "1.0",
  "fields": [
    {"field_name": "client_name", "description": "Full legal name of the client", "required": true},
    {"field_name": "client_address", "description": "Complete address of client", "required": true},
    {"field_name": "advocate_name", "description": "Full name of advocate", "required": true},
    {"field_name": "bar_council_number", "description": "Bar Council enrollment number", "required": true},
    {"field_name": "court_name", "description": "Name of court for which vakalatnama is executed", "required": true},
    {"field_name": "case_type", "description": "Type of case (Criminal/Civil)", "required": true},
    {"field_name": "case_number", "description": "Case number if assigned", "required": false},
    {"field_name": "date_of_execution", "description": "Date vakalatnama is signed (DD/MM/YYYY)", "required": true}
  ]
}''',

    'apps/templates_engine/registry.py': '''import json
from pathlib import Path

TEMPLATES_DIR = Path(__file__).parent / "templates"

class TemplateRegistry:
    _cache: dict = {}

    def __new__(cls):
        if not cls._cache:
            for f in TEMPLATES_DIR.glob("*.json"):
                t = json.loads(f.read_text())
                cls._cache[t["template_name"]] = t
        return super().__new__(cls)

    def get_template(self, name: str) -> dict:
        if name not in self._cache:
            raise KeyError(f"Template '{name}' not found")
        return self._cache[name]

    def list_templates(self) -> list[dict]:
        return [
            {"template_name": t["template_name"],
             "display_name": t["display_name"],
             "version": t["version"],
             "field_count": len(t["fields"]),
             "required_field_count": sum(1 for f in t["fields"] if f["required"])}
            for t in self._cache.values()
        ]
''',

    'apps/templates_engine/renderer.py': '''from apps.agents.schemas import TemplateVariable

class TemplateRenderer:
    def render(self, template: dict, variables: list[TemplateVariable]) -> str:
        var_map = {v.field_name: v for v in variables}
        rows = []
        for field in template["fields"]:
            name = field["field_name"]
            v = var_map.get(name)
            if v and not v.is_null:
                vector_ids = ",".join(v.source_vector_ids)
                rows.append(
                    f'<div class="field filled-field" data-field="{name}" '
                    f'data-vector-ids="{vector_ids}">'
                    f'<span class="field-label">{field["field_name"].replace("_"," ").title()}</span>'
                    f'<span class="field-value">{v.field_value}</span>'
                    f'</div>'
                )
            else:
                rows.append(
                    f'<div class="field null-field" data-field="{name}">'
                    f'<span class="field-label">{field["field_name"].replace("_"," ").title()}</span>'
                    f'<span class="field-value">[REQUIRED: {field["description"]} — Fill manually]</span>'
                    f'</div>'
                )
        return (
            f'<div class="lexai-document" data-template="{template["template_name"]}">'
            f'<h2 class="doc-title">{template["display_name"]}</h2>'
            + "".join(rows) +
            '</div>'
        )
''',

    'apps/orchestration/models.py': '''from django.db import models
import uuid

class QuerySession(models.Model):
    query_id      = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session_id    = models.UUIDField(db_index=True)
    raw_query     = models.TextField()
    status        = models.CharField(max_length=20, default="PENDING")
    intent        = models.CharField(max_length=50, blank=True)
    result_payload    = models.JSONField(null=True)
    verification_report = models.JSONField(null=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    completed_at  = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=["session_id", "created_at"])]


class AgentExecutionLog(models.Model):
    query        = models.ForeignKey(QuerySession, on_delete=models.CASCADE,
                                     related_name="agent_logs")
    agent_name   = models.CharField(max_length=100)
    status       = models.CharField(max_length=20)
    started_at   = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    duration_ms  = models.IntegerField(null=True)
    error_detail = models.TextField(blank=True)
''',

    'apps/orchestration/context_manager.py': '''import json
from uuid import UUID
from django.core.cache import cache
import redis
from django.conf import settings

_redis = redis.from_url(settings.REDIS_URL)

TTL = 86400  # 24h


class QueryContextManager:
    def _key(self, query_id, suffix): return f"lexai:ctx:{query_id}:{suffix}"

    def set(self, query_id: UUID, agent: str, data: dict):
        cache.set(self._key(query_id, agent), json.dumps(data), TTL)

    def get(self, query_id: UUID, agent: str) -> dict | None:
        raw = cache.get(self._key(query_id, agent))
        return json.loads(raw) if raw else None

    def set_status(self, query_id: UUID, status: str):
        cache.set(self._key(query_id, "status"), status, TTL)


class SSEPublisher:
    def publish(self, query_id: str, event: dict):
        _redis.publish(f"query:{query_id}:events", json.dumps(event))
''',

    'apps/orchestration/pipeline.py': '''from django.dispatch import Signal

pre_finalize_signal = Signal()  # Part 3 connects a receiver here


def finalize_pipeline(query_id, result_payload, context_manager, query_session):
    import json
    from django.utils import timezone
    query_session.result_payload = result_payload.model_dump(mode="json")
    query_session.status = "COMPLETE"
    query_session.completed_at = timezone.now()
    query_session.save(update_fields=["result_payload", "status", "completed_at"])
''',

    'apps/orchestration/dag_router.py': '''from uuid import UUID
from django.utils import timezone
from .models import QuerySession, AgentExecutionLog
from .context_manager import QueryContextManager, SSEPublisher
from .pipeline import pre_finalize_signal, finalize_pipeline
from apps.agents.schemas import QueryIntent, DRAFT_INTENTS, INTENT_TO_TEMPLATE
from apps.agents.intent_classifier import IntentClassifierAgent
from apps.agents.retrieval_agent import RetrievalAgent
from apps.agents.synthesis_agent import SynthesisAgent
from apps.agents.drafting_agent import DraftingAgent
from apps.documents.models import LegalDocument
from apps.agents.base import AgentExecutionError
import structlog

log = structlog.get_logger()


class DAGRouter:
    def execute(self, query_id: UUID, session_id: UUID, raw_query: str) -> dict:
        ctx = QueryContextManager()
        sse = SSEPublisher()
        qs, _ = QuerySession.objects.get_or_create(
            query_id=query_id,
            defaults={"session_id": session_id, "raw_query": raw_query, "status": "RUNNING"}
        )
        sse.publish(str(query_id), {"event": "pipeline_start", "query_id": str(query_id)})

        doc_types = list(
            LegalDocument.objects.filter(session_id=session_id, status="READY")
            .values_list("document_type", flat=True).distinct()
        )

        def run_agent(agent, name, *args, **kwargs):
            log_entry = AgentExecutionLog.objects.create(
                query=qs, agent_name=name, status="RUNNING",
                started_at=timezone.now()
            )
            sse.publish(str(query_id), {"event": "agent_start", "agent": name})
            try:
                result = agent.execute(*args, **kwargs)
                log_entry.status = "COMPLETE"
                log_entry.completed_at = timezone.now()
                log_entry.duration_ms = int(
                    (log_entry.completed_at - log_entry.started_at).total_seconds() * 1000
                )
                log_entry.save()
                sse.publish(str(query_id), {"event": "agent_complete", "agent": name,
                                            "duration_ms": log_entry.duration_ms})
                return result
            except AgentExecutionError as e:
                log_entry.status = "FAILED"
                log_entry.error_detail = str(e.cause)
                log_entry.save()
                qs.status = "FAILED"
                qs.save(update_fields=["status"])
                sse.publish(str(query_id), {"event": "pipeline_failed",
                                            "agent": name, "error": str(e.cause)})
                raise

        try:
            # Step 1: Intent
            intent_out = run_agent(
                IntentClassifierAgent(), "IntentClassifier",
                query_id=query_id, session_id=session_id,
                raw_query=raw_query, available_document_types=doc_types,
            )
            qs.intent = intent_out.intent.value
            qs.save(update_fields=["intent"])

            if intent_out.intent == QueryIntent.UNSUPPORTED:
                qs.status = "FAILED"
                qs.save(update_fields=["status"])
                return {"error": "Query type not supported."}

            # Step 2: Retrieval
            retrieval_out = run_agent(
                RetrievalAgent(), "Retrieval",
                session_id=session_id, query_id=query_id,
                rewritten_query=intent_out.rewritten_query,
                target_document_types=intent_out.target_document_types,
            )
            if retrieval_out.total_retrieved == 0:
                qs.status = "FAILED"
                qs.save(update_fields=["status"])
                sse.publish(str(query_id), {"event": "pipeline_failed",
                                            "error": "No relevant document content found."})
                return {"error": "No relevant content found in uploaded documents."}

            # Step 3: Synthesis or Drafting
            if intent_out.intent in DRAFT_INTENTS:
                template_name = INTENT_TO_TEMPLATE[intent_out.intent]
                result_payload = run_agent(
                    DraftingAgent(), "Drafting",
                    query_id=query_id, session_id=session_id,
                    template_name=template_name,
                    retrieved_chunks=retrieval_out.retrieved_chunks,
                )
            else:
                result_payload = run_agent(
                    SynthesisAgent(), "Synthesis",
                    query_id=query_id, raw_query=raw_query,
                    rewritten_query=intent_out.rewritten_query,
                    mode=intent_out.intent.value,
                    retrieved_chunks=retrieval_out.retrieved_chunks,
                )

            # Signal Part 3 before finalization
            pre_finalize_signal.send(
                sender=DAGRouter,
                query_id=query_id,
                session_id=session_id,
                context=ctx,
                result_payload=result_payload,
                query_session=qs,
            )

            finalize_pipeline(query_id, result_payload, ctx, qs)
            sse.publish(str(query_id), {"event": "pipeline_complete",
                                        "query_id": str(query_id), "status": "COMPLETE"})
            return qs.result_payload

        except AgentExecutionError:
            return {"error": "Pipeline execution failed."}
''',

    'apps/orchestration/tasks.py': '''from celery import shared_task
from .dag_router import DAGRouter
import uuid


@shared_task(bind=True, time_limit=300, soft_time_limit=240)
def task_execute_query(self, query_id: str, session_id: str, raw_query: str):
    return DAGRouter().execute(
        query_id=uuid.UUID(query_id),
        session_id=uuid.UUID(session_id),
        raw_query=raw_query,
    )
''',

    'apps/orchestration/views.py': '''import uuid, json
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import redis
from django.conf import settings
from .models import QuerySession
from .tasks import task_execute_query

_redis = redis.from_url(settings.REDIS_URL)


class SubmitQueryView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")
        raw_query  = request.data.get("raw_query", "").strip()
        if not session_id or not raw_query:
            return Response({"success": False, "error": "session_id and raw_query required"},
                            status=400)
        query_id = str(uuid.uuid4())
        QuerySession.objects.create(
            query_id=query_id, session_id=session_id,
            raw_query=raw_query, status="PENDING"
        )
        task = task_execute_query.delay(query_id, session_id, raw_query)
        return Response({"success": True, "data": {
            "query_id": query_id, "session_id": session_id,
            "status": "PENDING", "task_id": task.id,
            "stream_url": f"/api/v1/queries/{query_id}/stream/",
        }}, status=202)


class QueryDetailView(APIView):
    def get(self, request, query_id):
        try:
            qs = QuerySession.objects.get(query_id=query_id)
        except QuerySession.DoesNotExist:
            return Response({"success": False, "error": "Not found"}, status=404)
        logs = list(qs.agent_logs.values(
            "agent_name", "status", "started_at", "completed_at", "duration_ms", "error_detail"
        ))
        return Response({"success": True, "data": {
            "query_id": str(qs.query_id),
            "session_id": str(qs.session_id),
            "raw_query": qs.raw_query,
            "intent": qs.intent,
            "status": qs.status,
            "execution_trace": logs,
            "result_payload": qs.result_payload,
            "verification_report": qs.verification_report,
            "created_at": qs.created_at.isoformat(),
            "completed_at": qs.completed_at.isoformat() if qs.completed_at else None,
        }})


class QueryStreamView(APIView):
    def get(self, request, query_id):
        def event_stream():
            pubsub = _redis.pubsub()
            pubsub.subscribe(f"query:{query_id}:events")
            import time
            deadline = time.time() + 300
            for message in pubsub.listen():
                if time.time() > deadline:
                    break
                if message["type"] == "message":
                    data = message["data"].decode()
                    yield f"data: {data}\\n\\n"
                    parsed = json.loads(data)
                    if parsed.get("event") in ("pipeline_complete", "pipeline_failed"):
                        break
            pubsub.unsubscribe()
        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


class SessionQueriesView(APIView):
    def get(self, request, session_id):
        qs = QuerySession.objects.filter(session_id=session_id).order_by("-created_at")
        return Response({"success": True, "data": [
            {"query_id": str(q.query_id), "raw_query": q.raw_query,
             "intent": q.intent, "status": q.status,
             "created_at": q.created_at.isoformat()}
            for q in qs
        ]})
''',

    'apps/orchestration/urls.py': '''from django.urls import path
from . import views

urlpatterns = [
    path("queries/", views.SubmitQueryView.as_view()),
    path("queries/<str:query_id>/", views.QueryDetailView.as_view()),
    path("queries/<str:query_id>/stream/", views.QueryStreamView.as_view()),
    path("sessions/<str:session_id>/queries/", views.SessionQueriesView.as_view()),
]
'''
}

for k, v in files.items():
    os.makedirs(os.path.dirname(k) or '.', exist_ok=True)
    with open(k, 'w', encoding='utf-8') as f:
        f.write(v)

print("done")
