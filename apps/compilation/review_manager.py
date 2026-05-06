from django.utils import timezone
from .models import CompiledDocument, ReviewChecklistItem


class ReviewManager:
    def approve_clause(self, document_id, clause_index: int) -> dict:
        doc = CompiledDocument.objects.get(document_id=document_id)
        item = ReviewChecklistItem.objects.get(document=doc, clause_index=clause_index)
        if item.is_null_field:
            raise ValueError("NULL fields cannot be auto-approved.")
        item.is_approved = True
        item.approved_at = timezone.now()
        item.save()
        return self._recompute(doc)

    def approve_all(self, document_id) -> dict:
        doc = CompiledDocument.objects.get(document_id=document_id)
        ReviewChecklistItem.objects.filter(
            document=doc, is_null_field=False, is_approved=False
        ).update(is_approved=True, approved_at=timezone.now())
        return self._recompute(doc)

    def reset(self, document_id) -> dict:
        doc = CompiledDocument.objects.get(document_id=document_id)
        ReviewChecklistItem.objects.filter(document=doc).update(is_approved=False, approved_at=None)
        return self._recompute(doc)

    def _recompute(self, doc: CompiledDocument) -> dict:
        total = doc.review_items.count()
        non_null = doc.review_items.filter(is_null_field=False)
        approved = non_null.filter(is_approved=True).count()
        null_count = doc.review_items.filter(is_null_field=True).count()
        pct = (approved / non_null.count() * 100) if non_null.count() > 0 else 0.0
        can_export = pct >= 100.0
        status = (CompiledDocument.Status.REVIEW_COMPLETE
                  if can_export else CompiledDocument.Status.PENDING_REVIEW)
        doc.approved_clauses = approved
        doc.review_completion_pct = pct
        doc.status = status
        doc.save(update_fields=["approved_clauses", "review_completion_pct", "status"])
        return {"approved_clauses": approved, "total_clauses": total,
                "null_clauses": null_count, "review_completion_pct": pct,
                "can_export": can_export, "status": status}
