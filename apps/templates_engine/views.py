from rest_framework.response import Response
from rest_framework.views import APIView

from apps.templates_engine.registry import TemplateRegistry


class TemplateListView(APIView):
    def get(self, request):
        return Response(
            {
                "success": True,
                "data": TemplateRegistry().list_templates(),
                "error": None,
                "meta": {},
            }
        )


class TemplateDetailView(APIView):
    def get(self, request, template_name: str):
        try:
            template = TemplateRegistry().get_template(template_name)
        except KeyError:
            return Response(
                {
                    "success": False,
                    "data": None,
                    "error": "Template not found",
                    "meta": {},
                },
                status=404,
            )
        return Response(
            {
                "success": True,
                "data": template,
                "error": None,
                "meta": {},
            }
        )
