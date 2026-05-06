import uuid, json
from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import redis
from django.conf import settings
from .models import QuerySession
from .tasks import task_execute_query

_redis = redis.from_url(settings.REDIS_URL)


class SubmitQueryView(APIView):
    def post(self, request):
        session_id = request.data.get("session_id")
        raw_query  = request.data.get("raw_query", "").strip()
        if not session_id or not raw_query:
            return Response({"success": False, "error": "session_id and raw_query required"},
                            status=400)
        query_id = str(uuid.uuid4())
        QuerySession.objects.create(
            query_id=query_id, session_id=session_id,
            raw_query=raw_query, status="PENDING"
        )
        task = task_execute_query.delay(query_id, session_id, raw_query)
        return Response({"success": True, "data": {
            "query_id": query_id, "session_id": session_id,
            "status": "PENDING", "task_id": task.id,
            "stream_url": f"/api/v1/queries/{query_id}/stream/",
        }}, status=202)


class QueryDetailView(APIView):
    def get(self, request, query_id):
        try:
            qs = QuerySession.objects.get(query_id=query_id)
        except QuerySession.DoesNotExist:
            return Response({"success": False, "error": "Not found"}, status=404)
        logs = list(qs.agent_logs.values(
            "agent_name", "status", "started_at", "completed_at", "duration_ms", "error_detail"
        ))
        return Response({"success": True, "data": {
            "query_id": str(qs.query_id),
            "session_id": str(qs.session_id),
            "raw_query": qs.raw_query,
            "intent": qs.intent,
            "status": qs.status,
            "execution_trace": logs,
            "result_payload": qs.result_payload,
            "verification_report": qs.verification_report,
            "created_at": qs.created_at.isoformat(),
            "completed_at": qs.completed_at.isoformat() if qs.completed_at else None,
        }})


class QueryStreamView(APIView):
    def get(self, request, query_id):
        def event_stream():
            pubsub = _redis.pubsub()
            pubsub.subscribe(f"query:{query_id}:events")
            import time
            deadline = time.time() + 300
            for message in pubsub.listen():
                if time.time() > deadline:
                    break
                if message["type"] == "message":
                    data = message["data"].decode()
                    yield f"data: {data}\n\n"
                    parsed = json.loads(data)
                    if parsed.get("event") in ("pipeline_complete", "pipeline_failed"):
                        break
            pubsub.unsubscribe()
        return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


class SessionQueriesView(APIView):
    def get(self, request, session_id):
        qs = QuerySession.objects.filter(session_id=session_id).order_by("-created_at")
        return Response({"success": True, "data": [
            {"query_id": str(q.query_id), "raw_query": q.raw_query,
             "intent": q.intent, "status": q.status,
             "created_at": q.created_at.isoformat()}
            for q in qs
        ]})
