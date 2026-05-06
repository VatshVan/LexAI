from pydantic import BaseModel, Field
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
