from uuid import UUID, uuid4
from django.conf import settings
from pydantic import BaseModel
from .base import BaseAgent
from .schemas import DraftingOutput, TemplateVariable, FactualClaim, RetrievedChunk
from apps.claude_client.client import get_claude
from apps.templates_engine.registry import TemplateRegistry
from apps.templates_engine.renderer import TemplateRenderer
from .synthesis_agent import _trim_chunks, _format_chunks


class _ExtractedField(BaseModel):
    field_name: str
    field_value: str | None
    source_vector_ids: list[str]
    is_null: bool

class _ExtractionResponse(BaseModel):
    extracted_fields: list[_ExtractedField]


class DraftingAgent(BaseAgent):
    agent_name = "Drafting"

    def _execute(
        self,
        query_id: UUID,
        session_id: UUID,
        template_name: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> DraftingOutput:
        template = TemplateRegistry().get_template(template_name)
        chunks = _trim_chunks(retrieved_chunks, settings.MAX_CHUNK_TOKENS_PER_CALL)

        user_msg = (
            f"TEMPLATE FIELDS:\n{[f['field_name']+': '+f['description'] for f in template['fields']]}\n\n"
            f"CONTEXT CHUNKS:\n{_format_chunks(chunks)}"
        )
        resp = get_claude().sonnet_json("template_extraction", user_msg, _ExtractionResponse)

        variables = [
            TemplateVariable(
                field_name=f.field_name,
                field_value=None if f.is_null else f.field_value,
                source_vector_ids=f.source_vector_ids,
                is_null=f.is_null,
            )
            for f in resp.extracted_fields
        ]
        null_count = sum(1 for v in variables if v.is_null)
        filled_count = len(variables) - null_count
        draft_html = TemplateRenderer().render(template, variables)

        # Convert to FactualClaims for Part 3 verification
        claims = [
            FactualClaim(
                claim_id=uuid4(),
                claim_text=f"{v.field_name}: {v.field_value}",
                source_vector_ids=v.source_vector_ids,
                confidence=0.9,
                claim_type="template_extraction",
            )
            for v in variables if not v.is_null
        ]
        return DraftingOutput(
            query_id=query_id,
            template_name=template_name,
            template_variables=variables,
            null_field_count=null_count,
            filled_field_count=filled_count,
            draft_html=draft_html,
            draft_raw={"template": template, "variables": [v.model_dump() for v in variables]},
            claims=claims,
        )
