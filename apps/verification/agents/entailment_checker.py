"""
Cost optimization:
  Cosine fast-path (no API call): handles ~70% of claims
  Sonnet slow-path: only for 0.45 < cosine < 0.82
  Typical cost: ~1-2 Sonnet calls per query ≈ $0.003
"""
import numpy as np
from uuid import UUID
from pydantic import BaseModel
from apps.agents.base import BaseAgent
from apps.agents.schemas import FactualClaim
from apps.verification.schemas import AtomicClaim, EntailmentResult, VerificationVerdict
from apps.documents.services.embedding import EmbeddingService
from apps.vector_store.repository import VectorRepository
from apps.claude_client.client import get_claude
from django.conf import settings
import json


class _EntailmentResponse(BaseModel):
    entailment_score: float
    contradiction_score: float
    neutral_score: float
    reasoning: str


def _cosine(a, b):
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


class EntailmentCheckerAgent(BaseAgent):
    agent_name = "EntailmentChecker"

    def _execute(
        self,
        atomic_claims: list[AtomicClaim],
        original_claims: list[FactualClaim],
    ) -> list[EntailmentResult]:
        claim_map = {c.claim_id: c for c in original_claims}
        embed = EmbeddingService()
        repo = VectorRepository()
        results = []

        HI = settings.COSINE_VERIFIED_THRESHOLD
        LO = settings.COSINE_HALLUCINATED_THRESHOLD

        for ac in atomic_claims:
            parent = claim_map.get(ac.parent_claim_id)
            if not parent:
                continue
            query_vec = embed.embed_query(ac.atomic_text)

            for vid in parent.source_vector_ids:
                vdoc = repo.get_by_vector_id(str(parent.source_vector_ids[0].split(":")[0]), vid)
                if not vdoc:
                    continue
                # Cosine fast-path
                if vdoc.embedding:
                    cosine = _cosine(query_vec, vdoc.embedding)
                    if cosine >= HI:
                        verdict = VerificationVerdict.VERIFIED
                        e, c, n = cosine, 0.0, 1-cosine
                        method = "cosine"
                    elif cosine <= LO:
                        verdict = VerificationVerdict.HALLUCINATED
                        e, c, n = 0.0, cosine, 1-cosine
                        method = "cosine"
                    else:
                        # Slow-path: Claude entailment
                        user_msg = f"CLAIM: {ac.atomic_text}\nSOURCE: {vdoc.text}"
                        try:
                            resp = get_claude().sonnet_json(
                                "entailment_scoring", user_msg, _EntailmentResponse)
                            e, c, n = resp.entailment_score, resp.contradiction_score, resp.neutral_score
                        except Exception:
                            e, c, n = cosine, 0.0, 1-cosine
                        verdict = (VerificationVerdict.VERIFIED if e >= 0.70
                                   else VerificationVerdict.HALLUCINATED if e <= 0.30
                                   else VerificationVerdict.INSUFFICIENT)
                        method = "cross_encoder"
                else:
                    e, c, n = 0.5, 0.0, 0.5
                    verdict = VerificationVerdict.INSUFFICIENT
                    method = "no_embedding"

                results.append(EntailmentResult(
                    atomic_claim_id=ac.atomic_claim_id,
                    source_vector_id=vid,
                    source_text=vdoc.text[:300],
                    entailment_score=e,
                    contradiction_score=c,
                    neutral_score=n,
                    verdict=verdict,
                    scorer_method=method,
                ))
        return results
