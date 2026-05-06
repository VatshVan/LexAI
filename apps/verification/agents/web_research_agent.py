"""
Cost: Haiku for verdict ≈ $0.0001 per claim checked
Only runs on claims that are INSUFFICIENT AND require_external_check=True
Typical: 0-2 claims per query ≈ $0.0002
"""
import httpx
import re
import json
from pydantic import BaseModel
from apps.agents.base import BaseAgent
from apps.verification.schemas import AtomicClaim, EntailmentResult, WebResearchResult, VerificationVerdict
from apps.claude_client.client import get_claude

WHITELIST = {
    "indiankanoon.org", "legislative.gov.in", "main.sci.gov.in",
    "districts.ecourts.gov.in", "bombayhighcourt.nic.in",
    "delhihighcourt.nic.in", "barandbench.com", "livelaw.in",
}

class _VerdictResponse(BaseModel):
    supports_claim: bool
    confidence: float
    reasoning: str


class WebResearchAgent(BaseAgent):
    agent_name = "WebResearch"

    def _execute(
        self,
        atomic_claims: list[AtomicClaim],
        entailment_results: list[EntailmentResult],
    ) -> list[WebResearchResult]:
        ent_map = {r.atomic_claim_id: r for r in entailment_results}
        results = []

        eligible = [
            ac for ac in atomic_claims
            if ac.requires_external_check
            and ent_map.get(ac.atomic_claim_id, None) is not None
            and ent_map[ac.atomic_claim_id].verdict == VerificationVerdict.INSUFFICIENT
        ]

        for ac in eligible:
            result = self._research_claim(ac)
            if result:
                results.append(result)
        return results

    def _research_claim(self, ac: AtomicClaim) -> WebResearchResult | None:
        import urllib.parse
        query = urllib.parse.quote(ac.atomic_text[:100])
        url = f"https://indiankanoon.org/search/?formInput={query}"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True,
                              headers={"User-Agent": "LexAI-Research/1.0"}) as client:
                resp = client.get(url)
            text = re.sub(r"<[^>]+>", " ", resp.text)
            text = re.sub(r"\s+", " ", text).strip()[:500]
            if len(text) < 50:
                return None
        except Exception:
            return None

        user_msg = f"CLAIM: {ac.atomic_text}\nRETRIEVED: {text}\nURL: {url}"
        try:
            verdict_resp = get_claude().haiku_json("web_research_verdict", user_msg, _VerdictResponse)
        except Exception:
            return None

        return WebResearchResult(
            atomic_claim_id=ac.atomic_claim_id,
            query_used=ac.atomic_text[:100],
            source_url=url,
            retrieved_text=text,
            supports_claim=verdict_resp.supports_claim,
            verdict=VerificationVerdict.EXTERNALLY_VERIFIED
            if verdict_resp.supports_claim else VerificationVerdict.EXTERNALLY_FAILED,
        )
