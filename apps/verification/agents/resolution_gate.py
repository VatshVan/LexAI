import statistics
from uuid import UUID
from apps.agents.base import BaseAgent
from apps.agents.schemas import FactualClaim
from apps.verification.schemas import (
    AtomicClaim, EntailmentResult, WebResearchResult,
    ClaimVerificationSummary, VerificationVerdict,
)
from django.conf import settings

E_WEIGHT = 0.70
W_WEIGHT = 0.30


class ResolutionGate(BaseAgent):
    agent_name = "ResolutionGate"

    def _execute(
        self,
        original_claims: list[FactualClaim],
        atomic_claims: list[AtomicClaim],
        entailment_results: list[EntailmentResult],
        web_research_results: list[WebResearchResult],
    ) -> tuple[list[FactualClaim], list[ClaimVerificationSummary]]:
        ent_by_ac = {}
        for e in entailment_results:
            ent_by_ac.setdefault(e.atomic_claim_id, []).append(e)
        web_by_ac = {w.atomic_claim_id: w for w in web_research_results}
        ac_by_parent = {}
        for ac in atomic_claims:
            ac_by_parent.setdefault(ac.parent_claim_id, []).append(ac)

        verified, summaries = [], []
        PURGE = settings.PURGE_SCORE_THRESHOLD
        CONTRA = settings.CONTRADICTION_PURGE_THRESHOLD

        for claim in original_claims:
            atomics = ac_by_parent.get(claim.claim_id, [])
            if not atomics:
                # No atomics generated — keep as insufficient
                summaries.append(ClaimVerificationSummary(
                    claim_id=claim.claim_id,
                    atomic_claims=[], entailment_results=[], web_research_results=[],
                    final_verdict=VerificationVerdict.INSUFFICIENT,
                    final_score=0.5, citation_string="", purge_reason=None,
                ))
                claim.is_flagged = True
                verified.append(claim)
                continue

            atomic_scores = []
            direct_contradiction = False
            best_source = None

            for ac in atomics:
                ents = ent_by_ac.get(ac.atomic_claim_id, [])
                if not ents:
                    atomic_scores.append(0.5)
                    continue
                best_ent = max(ents, key=lambda e: e.entailment_score)
                if best_ent.contradiction_score > CONTRA:
                    direct_contradiction = True
                    break
                if not best_source or best_ent.entailment_score > (best_source.entailment_score if best_source else 0):
                    best_source = best_ent

                web = web_by_ac.get(ac.atomic_claim_id)
                if web:
                    score = best_ent.entailment_score * E_WEIGHT + (1.0 if web.supports_claim else 0.0) * W_WEIGHT
                else:
                    score = best_ent.entailment_score
                atomic_scores.append(score)

            if direct_contradiction:
                verdict = VerificationVerdict.PURGED
                final_score = 0.0
                purge_reason = "direct_contradiction"
            else:
                final_score = statistics.mean(atomic_scores) if atomic_scores else 0.0
                # NULL template fields: never purge
                if claim.claim_type == "template_extraction" and claim.claim_text.endswith("NULL"):
                    verdict = VerificationVerdict.INSUFFICIENT
                    purge_reason = None
                elif final_score >= 0.70:
                    verdict = VerificationVerdict.VERIFIED
                    purge_reason = None
                elif final_score >= 0.50:
                    verdict = VerificationVerdict.INSUFFICIENT
                    purge_reason = None
                else:
                    verdict = VerificationVerdict.PURGED
                    purge_reason = f"low_composite_score:{final_score:.2f}"

            # Citation string from best source
            citation = ""
            if best_source and verdict != VerificationVerdict.PURGED:
                m = best_source.source_text
                citation = f"[Src: {best_source.source_vector_id[:8]}]"

            summaries.append(ClaimVerificationSummary(
                claim_id=claim.claim_id,
                atomic_claims=atomics,
                entailment_results=ent_by_ac.get(
                    atomics[0].atomic_claim_id, []) if atomics else [],
                web_research_results=[web_by_ac[ac.atomic_claim_id]
                                       for ac in atomics if ac.atomic_claim_id in web_by_ac],
                final_verdict=verdict,
                final_score=final_score,
                citation_string=citation,
                purge_reason=purge_reason,
            ))

            if verdict != VerificationVerdict.PURGED:
                claim.is_verified = (verdict == VerificationVerdict.VERIFIED)
                claim.is_flagged = (verdict == VerificationVerdict.INSUFFICIENT)
                claim.verification_score = final_score
                verified.append(claim)

        return verified, summaries
