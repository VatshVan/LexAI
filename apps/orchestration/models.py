from django.db import models
import uuid

class QuerySession(models.Model):
    query_id      = models.UUIDField(primary_key=True, default=uuid.uuid4)
    session_id    = models.UUIDField(db_index=True)
    raw_query     = models.TextField()
    status        = models.CharField(max_length=20, default="PENDING")
    intent        = models.CharField(max_length=50, blank=True)
    result_payload    = models.JSONField(null=True)
    verification_report = models.JSONField(null=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    completed_at  = models.DateTimeField(null=True)

    class Meta:
        indexes = [models.Index(fields=["session_id", "created_at"])]


class AgentExecutionLog(models.Model):
    query        = models.ForeignKey(QuerySession, on_delete=models.CASCADE,
                                     related_name="agent_logs")
    agent_name   = models.CharField(max_length=100)
    status       = models.CharField(max_length=20)
    started_at   = models.DateTimeField(null=True)
    completed_at = models.DateTimeField(null=True)
    duration_ms  = models.IntegerField(null=True)
    error_detail = models.TextField(blank=True)
