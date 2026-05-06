from celery import shared_task
from .dag_router import DAGRouter
import uuid


@shared_task(bind=True, time_limit=300, soft_time_limit=240)
def task_execute_query(self, query_id: str, session_id: str, raw_query: str):
    return DAGRouter().execute(
        query_id=uuid.UUID(query_id),
        session_id=uuid.UUID(session_id),
        raw_query=raw_query,
    )
