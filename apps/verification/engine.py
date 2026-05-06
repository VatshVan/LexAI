from uuid import UUID
from time import perf_counter
from apps.agents.schemas import FactualClaim
from apps.verification.agents.claim_parser import ClaimParserAgent
from apps.verification.agents.entailment_checker import EntailmentCheckerAgent
from apps.verification.agents.web_research_agent import WebResearchAgent
from apps.verification.agents.resolution_gate import ResolutionGate
from apps.verification.schemas import VerificationReport, VerificationVerdict
from apps.orchestration.context_manager import SSEPublisher
import structlog

log = structlog.get_logger()


class VerificationEngine:
    def run(
        self,
        query_id: UUID,
        session_id: UUID,
        claims: list[FactualClaim],
    ) -> tuple[list[FactualClaim], VerificationReport]:
        sse = SSEPublisher()
        start = perf_counter()
        qid = str(query_id)
        sse.publish(qid, {"event": "verification_start", "total_claims": len(claims)})

        atomic_claims = ClaimParserAgent().execute(claims)
        sse.publish(qid, {"event": "agent_complete", "agent": "ClaimParser",
                          "atomic_claims": len(atomic_claims)})

        entailment_results = EntailmentCheckerAgent().execute(
            atomic_claims=atomic_claims, original_claims=claims)
        sse.publish(qid, {"event": "agent_complete", "agent": "EntailmentChecker"})

        eligible_for_web = [
            ac for ac in atomic_claims
            if ac.requires_external_check
            and any(e.atomic_claim_id == ac.atomic_claim_id
                    and e.verdict.value in ("INSUFFICIENT",)
                    for e in entailment_results)
        ]
        agents_used = ["ClaimParser", "EntailmentChecker"]
        if eligible_for_web:
            web_results = WebResearchAgent().execute(
                atomic_claims=eligible_for_web,
                entailment_results=entailment_results,
            )
            agents_used.append("WebResearch")
            sse.publish(qid, {"event": "agent_complete", "agent": "WebResearch",
                              "checked": len(web_results)})
        else:
            web_results = []
            sse.publish(qid, {"event": "agent_skipped", "agent": "WebResearch"})

        verified_claims, summaries = ResolutionGate().execute(
            original_claims=claims,
            atomic_claims=atomic_claims,
            entailment_results=entailment_results,
            web_research_results=web_results,
        )
        agents_used.append("ResolutionGate")

        purged = [s for s in summaries if s.final_verdict == VerificationVerdict.PURGED]
        ev_count = sum(1 for s in summaries
                       if s.final_verdict == VerificationVerdict.EXTERNALLY_VERIFIED)

        report = VerificationReport(
            query_id=query_id,
            total_claims_received=len(claims),
            total_claims_verified=len([s for s in summaries
                                        if s.final_verdict == VerificationVerdict.VERIFIED]),
            total_claims_purged=len(purged),
            total_claims_externally_verified=ev_count,
            verification_score=len(verified_claims) / max(len(claims), 1),
            claim_summaries=summaries,
            verified_claims=[c.claim_id for c in verified_claims],
            purged_claims=[s.claim_id for s in purged],
            verification_duration_ms=int((perf_counter() - start) * 1000),
            agents_used=agents_used,
        )
        sse.publish(qid, {"event": "verification_complete",
                          "score": report.verification_score,
                          "passed": len(verified_claims),
                          "purged": len(purged)})
        return verified_claims, report
