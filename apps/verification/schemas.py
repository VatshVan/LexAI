from pydantic import BaseModel, Field
from enum import Enum
from uuid import UUID, uuid4

class VerificationVerdict(str, Enum):
    VERIFIED             = "VERIFIED"
    INSUFFICIENT         = "INSUFFICIENT"
    HALLUCINATED         = "HALLUCINATED"
    EXTERNALLY_VERIFIED  = "EXTERNALLY_VERIFIED"
    EXTERNALLY_FAILED    = "EXTERNALLY_FAILED"
    PURGED               = "PURGED"

class AtomicClaim(BaseModel):
    atomic_claim_id: UUID = Field(default_factory=uuid4)
    parent_claim_id: UUID
    atomic_text: str
    subject: str
    predicate: str
    requires_external_check: bool = False

class EntailmentResult(BaseModel):
    atomic_claim_id: UUID
    source_vector_id: str
    source_text: str
    entailment_score: float
    contradiction_score: float
    neutral_score: float
    verdict: VerificationVerdict
    scorer_method: str

class WebResearchResult(BaseModel):
    atomic_claim_id: UUID
    query_used: str
    source_url: str
    retrieved_text: str
    supports_claim: bool
    verdict: VerificationVerdict

class ClaimVerificationSummary(BaseModel):
    claim_id: UUID
    atomic_claims: list[AtomicClaim]
    entailment_results: list[EntailmentResult]
    web_research_results: list[WebResearchResult]
    final_verdict: VerificationVerdict
    final_score: float
    citation_string: str
    purge_reason: str | None

class VerificationReport(BaseModel):
    query_id: UUID
    total_claims_received: int
    total_claims_verified: int
    total_claims_purged: int
    total_claims_externally_verified: int
    verification_score: float
    claim_summaries: list[ClaimVerificationSummary]
    verified_claims: list[UUID]
    purged_claims: list[UUID]
    verification_duration_ms: int
    agents_used: list[str]
