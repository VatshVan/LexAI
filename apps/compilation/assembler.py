from uuid import UUID
from apps.agents.schemas import FactualClaim, DraftingOutput, SynthesisOutput
from apps.verification.schemas import ClaimVerificationSummary, VerificationVerdict
from .models import CompiledDocument, ReviewChecklistItem
from apps.orchestration.models import QuerySession


class AssemblerService:
    def assemble(
        self,
        query_id: UUID,
        verified_claims: list[FactualClaim],
        summaries: list[ClaimVerificationSummary],
        result_payload,
    ) -> CompiledDocument:
        qs = QuerySession.objects.get(query_id=query_id)
        summary_map = {str(s.claim_id): s for s in summaries}

        is_drafting = isinstance(result_payload, DraftingOutput)

        doc = CompiledDocument.objects.create(
            query=qs,
            status=CompiledDocument.Status.ASSEMBLING,
            template_name=result_payload.template_name if is_drafting else "",
            assembled_html="",
            total_clauses=len(verified_claims),
        )

        items, html_parts = [], []
        for idx, claim in enumerate(verified_claims):
            s = summary_map.get(str(claim.claim_id))
            verdict = s.final_verdict.value if s else "UNKNOWN"
            citation = s.citation_string if s else ""
            score = s.final_score if s else 0.0

            is_null = is_drafting and claim.claim_text.split(":", 1)[-1].strip() == "None"
            css_class = "null-field" if is_null else (
                "verified" if verdict == "VERIFIED" else "insufficient")

            citation_html = (
                f'<span class="citation">{citation}</span>'
                if citation else "")
            flag_html = (
                '<p class="flag">⚠ Verify manually — evidence inconclusive</p>'
                if verdict == "INSUFFICIENT" else "")
            null_html = (
                '<p class="null-notice">[REQUIRED — Fill before filing]</p>'
                if is_null else "")

            html_parts.append(
                f'<div class="clause {css_class}" '
                f'data-claim-id="{claim.claim_id}" '
                f'data-vector-ids="{",".join(claim.source_vector_ids)}" '
                f'data-score="{score:.2f}">'
                f'<p class="clause-text">{claim.claim_text}</p>'
                f'{citation_html}'
                f'{flag_html}'
                f'{null_html}'
                f'</div>'
            )
            items.append(ReviewChecklistItem(
                document=doc, clause_index=idx,
                clause_text=claim.claim_text,
                citation_string=citation,
                source_vector_ids=claim.source_vector_ids,
                verification_verdict=verdict,
                verification_score=score,
                is_null_field=is_null,
                is_approved=False,
            ))

        ReviewChecklistItem.objects.bulk_create(items)
        doc.assembled_html = (
            '<div class="lexai-analysis-result">' + "".join(html_parts) + "</div>"
        )
        doc.status = CompiledDocument.Status.PENDING_REVIEW
        doc.total_clauses = len(items)
        doc.save()
        return doc
