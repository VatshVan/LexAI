from django.db import models
import uuid

class CompiledDocument(models.Model):
    class Status(models.TextChoices):
        ASSEMBLING      = "ASSEMBLING"
        PENDING_REVIEW  = "PENDING_REVIEW"
        REVIEW_COMPLETE = "REVIEW_COMPLETE"
        EXPORTED        = "EXPORTED"

    document_id           = models.UUIDField(primary_key=True, default=uuid.uuid4)
    query                 = models.OneToOneField(
        "orchestration.QuerySession", on_delete=models.CASCADE,
        related_name="compiled_document"
    )
    status                = models.CharField(max_length=20, default=Status.ASSEMBLING)
    template_name         = models.CharField(max_length=100, blank=True)
    assembled_html        = models.TextField()
    review_completion_pct = models.FloatField(default=0.0)
    total_clauses         = models.PositiveIntegerField(default=0)
    approved_clauses      = models.PositiveIntegerField(default=0)
    export_pdf_path       = models.CharField(max_length=500, blank=True)
    export_docx_path      = models.CharField(max_length=500, blank=True)
    exported_at           = models.DateTimeField(null=True)
    created_at            = models.DateTimeField(auto_now_add=True)


class ReviewChecklistItem(models.Model):
    document            = models.ForeignKey(CompiledDocument, on_delete=models.CASCADE,
                                            related_name="review_items")
    clause_index        = models.PositiveIntegerField()
    clause_text         = models.TextField()
    citation_string     = models.CharField(max_length=500, blank=True)
    source_vector_ids   = models.JSONField(default=list)
    verification_verdict= models.CharField(max_length=30, blank=True)
    verification_score  = models.FloatField(default=0.0)
    is_null_field       = models.BooleanField(default=False)
    is_approved         = models.BooleanField(default=False)
    approved_at         = models.DateTimeField(null=True)

    class Meta:
        unique_together = [("document", "clause_index")]
        ordering = ["clause_index"]
