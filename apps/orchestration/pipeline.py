from django.dispatch import Signal

pre_finalize_signal = Signal()  # Part 3 connects a receiver here


def finalize_pipeline(query_id, result_payload, context_manager, query_session):
    import json
    from django.utils import timezone
    query_session.result_payload = result_payload.model_dump(mode="json")
    query_session.status = "COMPLETE"
    query_session.completed_at = timezone.now()
    query_session.save(update_fields=["result_payload", "status", "completed_at"])
