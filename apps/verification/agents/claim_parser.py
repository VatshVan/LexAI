"""
Cost: Haiku, ~200 input + 100 output per batch of 10 claims ≈ $0.0003
Fast path: template_extraction claims skip Claude (already atomic).
"""
from uuid import UUID, uuid4
from pydantic import BaseModel
from apps.agents.base import BaseAgent
from apps.agents.schemas import FactualClaim
from apps.verification.schemas import AtomicClaim
from apps.claude_client.client import get_claude
import json

class _AtomicResponse(BaseModel):
    atomic_claims: list[dict]


class ClaimParserAgent(BaseAgent):
    agent_name = "ClaimParser"

    def _execute(self, claims: list[FactualClaim]) -> list[AtomicClaim]:
        result = []
        batch, batch_ids = [], []

        for claim in claims:
            if claim.claim_type == "template_extraction":
                # Fast path: already atomic
                result.append(AtomicClaim(
                    parent_claim_id=claim.claim_id,
                    atomic_text=claim.claim_text,
                    subject=claim.claim_text.split(":")[0] if ":" in claim.claim_text else "",
                    predicate=claim.claim_text.split(":", 1)[1].strip() if ":" in claim.claim_text else claim.claim_text,
                    requires_external_check=False,
                ))
            else:
                batch.append(f"CLAIM_ID:{claim.claim_id}\n{claim.claim_text}")
                batch_ids.append(claim.claim_id)

            if len(batch) == 10:
                result.extend(self._call_claude(batch, batch_ids))
                batch, batch_ids = [], []

        if batch:
            result.extend(self._call_claude(batch, batch_ids))
        return result

    def _call_claude(self, batch: list[str], ids: list[UUID]) -> list[AtomicClaim]:
        user_msg = "DECOMPOSE EACH:\n\n" + "\n---\n".join(batch)
        try:
            raw = get_claude().haiku("claim_decomposition", user_msg)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            atomics = data.get("atomic_claims", [])
        except Exception:
            # Fallback: treat each claim as its own atomic
            return [AtomicClaim(parent_claim_id=cid, atomic_text=b.split("\n", 1)[1],
                                subject="", predicate="", requires_external_check=False)
                    for b, cid in zip(batch, ids)]

        result = []
        for i, a in enumerate(atomics):
            parent_id = ids[i] if i < len(ids) else ids[-1]
            result.append(AtomicClaim(
                parent_claim_id=parent_id,
                atomic_text=a.get("atomic_text", ""),
                subject=a.get("subject", ""),
                predicate=a.get("predicate", ""),
                requires_external_check=a.get("requires_external_check", False),
            ))
        return result
