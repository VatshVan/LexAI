from uuid import UUID
from django.utils import timezone
from .models import QuerySession, AgentExecutionLog
from .context_manager import QueryContextManager, SSEPublisher
from .pipeline import pre_finalize_signal, finalize_pipeline
from apps.agents.schemas import QueryIntent, DRAFT_INTENTS, INTENT_TO_TEMPLATE
from apps.agents.intent_classifier import IntentClassifierAgent
from apps.agents.retrieval_agent import RetrievalAgent
from apps.agents.synthesis_agent import SynthesisAgent
from apps.agents.drafting_agent import DraftingAgent
from apps.documents.models import LegalDocument
from apps.agents.base import AgentExecutionError
import structlog

log = structlog.get_logger()


class DAGRouter:
    def execute(self, query_id: UUID, session_id: UUID, raw_query: str) -> dict:
        ctx = QueryContextManager()
        sse = SSEPublisher()
        qs, _ = QuerySession.objects.get_or_create(
            query_id=query_id,
            defaults={"session_id": session_id, "raw_query": raw_query, "status": "RUNNING"}
        )
        sse.publish(str(query_id), {"event": "pipeline_start", "query_id": str(query_id)})

        doc_types = list(
            LegalDocument.objects.filter(session_id=session_id, status="READY")
            .values_list("document_type", flat=True).distinct()
        )

        def run_agent(agent, name, *args, **kwargs):
            log_entry = AgentExecutionLog.objects.create(
                query=qs, agent_name=name, status="RUNNING",
                started_at=timezone.now()
            )
            sse.publish(str(query_id), {"event": "agent_start", "agent": name})
            try:
                result = agent.execute(*args, **kwargs)
                log_entry.status = "COMPLETE"
                log_entry.completed_at = timezone.now()
                log_entry.duration_ms = int(
                    (log_entry.completed_at - log_entry.started_at).total_seconds() * 1000
                )
                log_entry.save()
                sse.publish(str(query_id), {"event": "agent_complete", "agent": name,
                                            "duration_ms": log_entry.duration_ms})
                return result
            except AgentExecutionError as e:
                log_entry.status = "FAILED"
                log_entry.error_detail = str(e.cause)
                log_entry.save()
                qs.status = "FAILED"
                qs.save(update_fields=["status"])
                sse.publish(str(query_id), {"event": "pipeline_failed",
                                            "agent": name, "error": str(e.cause)})
                raise

        try:
            # Step 1: Intent
            intent_out = run_agent(
                IntentClassifierAgent(), "IntentClassifier",
                query_id=query_id, session_id=session_id,
                raw_query=raw_query, available_document_types=doc_types,
            )
            qs.intent = intent_out.intent.value
            qs.save(update_fields=["intent"])

            if intent_out.intent == QueryIntent.UNSUPPORTED:
                qs.status = "FAILED"
                qs.save(update_fields=["status"])
                return {"error": "Query type not supported."}

            # Step 2: Retrieval
            retrieval_out = run_agent(
                RetrievalAgent(), "Retrieval",
                session_id=session_id, query_id=query_id,
                rewritten_query=intent_out.rewritten_query,
                target_document_types=intent_out.target_document_types,
            )
            if retrieval_out.total_retrieved == 0:
                qs.status = "FAILED"
                qs.save(update_fields=["status"])
                sse.publish(str(query_id), {"event": "pipeline_failed",
                                            "error": "No relevant document content found."})
                return {"error": "No relevant content found in uploaded documents."}

            # Step 3: Synthesis or Drafting
            if intent_out.intent in DRAFT_INTENTS:
                template_name = INTENT_TO_TEMPLATE[intent_out.intent]
                result_payload = run_agent(
                    DraftingAgent(), "Drafting",
                    query_id=query_id, session_id=session_id,
                    template_name=template_name,
                    retrieved_chunks=retrieval_out.retrieved_chunks,
                )
            else:
                result_payload = run_agent(
                    SynthesisAgent(), "Synthesis",
                    query_id=query_id, raw_query=raw_query,
                    rewritten_query=intent_out.rewritten_query,
                    mode=intent_out.intent.value,
                    retrieved_chunks=retrieval_out.retrieved_chunks,
                )

            # Signal Part 3 before finalization
            pre_finalize_signal.send(
                sender=DAGRouter,
                query_id=query_id,
                session_id=session_id,
                context=ctx,
                result_payload=result_payload,
                query_session=qs,
            )

            finalize_pipeline(query_id, result_payload, ctx, qs)
            sse.publish(str(query_id), {"event": "pipeline_complete",
                                        "query_id": str(query_id), "status": "COMPLETE"})
            return qs.result_payload

        except AgentExecutionError:
            return {"error": "Pipeline execution failed."}
