import json
from uuid import UUID
from django.core.cache import cache
import redis
from django.conf import settings

_redis = redis.from_url(settings.REDIS_URL)

TTL = 86400  # 24h


class QueryContextManager:
    def _key(self, query_id, suffix): return f"lexai:ctx:{query_id}:{suffix}"

    def set(self, query_id: UUID, agent: str, data: dict):
        cache.set(self._key(query_id, agent), json.dumps(data), TTL)

    def get(self, query_id: UUID, agent: str) -> dict | None:
        raw = cache.get(self._key(query_id, agent))
        return json.loads(raw) if raw else None

    def set_status(self, query_id: UUID, status: str):
        cache.set(self._key(query_id, "status"), status, TTL)


class SSEPublisher:
    def publish(self, query_id: str, event: dict):
        _redis.publish(f"query:{query_id}:events", json.dumps(event))
