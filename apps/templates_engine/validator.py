from apps.agents.schemas import TemplateVariable


class TemplateValidator:
    def validate(self, template: dict, variables: list[TemplateVariable]) -> dict:
        variable_map = {variable.field_name: variable for variable in variables}
        missing_required = []
        for field in template["fields"]:
            variable = variable_map.get(field["field_name"])
            if field["required"] and (variable is None or variable.is_null):
                missing_required.append(field["field_name"])
        return {
            "is_valid": not missing_required,
            "missing_required_fields": missing_required,
        }
