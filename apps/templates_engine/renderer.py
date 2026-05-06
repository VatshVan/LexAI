from apps.agents.schemas import TemplateVariable

class TemplateRenderer:
    def render(self, template: dict, variables: list[TemplateVariable]) -> str:
        var_map = {v.field_name: v for v in variables}
        rows = []
        for field in template["fields"]:
            name = field["field_name"]
            v = var_map.get(name)
            if v and not v.is_null:
                vector_ids = ",".join(v.source_vector_ids)
                rows.append(
                    f'<div class="field filled-field" data-field="{name}" '
                    f'data-vector-ids="{vector_ids}">'
                    f'<span class="field-label">{field["field_name"].replace("_"," ").title()}</span>'
                    f'<span class="field-value">{v.field_value}</span>'
                    f'</div>'
                )
            else:
                rows.append(
                    f'<div class="field null-field" data-field="{name}">'
                    f'<span class="field-label">{field["field_name"].replace("_"," ").title()}</span>'
                    f'<span class="field-value">[REQUIRED: {field["description"]} — Fill manually]</span>'
                    f'</div>'
                )
        return (
            f'<div class="lexai-document" data-template="{template["template_name"]}">'
            f'<h2 class="doc-title">{template["display_name"]}</h2>'
            + "".join(rows) +
            '</div>'
        )
