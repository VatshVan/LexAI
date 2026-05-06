from uuid import UUID
from pydantic import BaseModel
from .base import BaseAgent
from .schemas import IntentClassificationOutput, QueryIntent
from apps.claude_client.client import get_claude


class _ClaudeIntentResponse(BaseModel):
    intent: str
    rewritten_query: str
    target_document_types: list[str]
    confidence: float
    reasoning: str


class IntentClassifierAgent(BaseAgent):
    agent_name = "IntentClassifier"

    def _execute(
        self,
        query_id: UUID,
        session_id: UUID,
        raw_query: str,
        available_document_types: list[str],
    ) -> IntentClassificationOutput:
        user_msg = (
            f"QUERY: {raw_query}\n"
            f"AVAILABLE_DOC_TYPES: {', '.join(available_document_types)}"
        )
        resp = get_claude().haiku_json(
            "intent_classification", user_msg, _ClaudeIntentResponse
        )
        intent = QueryIntent(resp.intent) if resp.intent in QueryIntent._value2member_map_ \
            else QueryIntent.FACTUAL_QUERY
        if resp.confidence < 0.5:
            intent = QueryIntent.FACTUAL_QUERY
        return IntentClassificationOutput(
            query_id=query_id,
            intent=intent,
            rewritten_query=resp.rewritten_query,
            target_document_types=resp.target_document_types,
            confidence=resp.confidence,
            reasoning=resp.reasoning,
        )
