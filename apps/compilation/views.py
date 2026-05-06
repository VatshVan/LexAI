from django.http import FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import CompiledDocument, ReviewChecklistItem
from .review_manager import ReviewManager
from .exporters.base import ExportNotPermittedError
from .exporters.pdf_exporter import PDFExporter
from .exporters.docx_exporter import DOCXExporter
from pathlib import Path


def _checklist_data(doc):
    items = list(doc.review_items.values(
        "clause_index", "clause_text", "citation_string", "source_vector_ids",
        "verification_verdict", "verification_score", "is_null_field",
        "is_approved", "approved_at",
    ))
    return {
        "document_id": str(doc.document_id),
        "query_id": str(doc.query_id),
        "status": doc.status,
        "template_name": doc.template_name,
        "assembled_html": doc.assembled_html,
        "review_completion_pct": doc.review_completion_pct,
        "total_clauses": doc.total_clauses,
        "approved_clauses": doc.approved_clauses,
        "can_export": doc.status == CompiledDocument.Status.REVIEW_COMPLETE,
        "checklist": items,
    }


class CompiledDocumentView(APIView):
    def get(self, request, query_id):
        try:
            doc = CompiledDocument.objects.get(query__query_id=query_id)
        except CompiledDocument.DoesNotExist:
            return Response({"success": False, "error": "Not found"}, status=404)
        return Response({"success": True, "data": _checklist_data(doc)})


class ApproveClauseView(APIView):
    def post(self, request, query_id, clause_index):
        doc = CompiledDocument.objects.get(query__query_id=query_id)
        try:
            data = ReviewManager().approve_clause(doc.document_id, clause_index)
            return Response({"success": True, "data": data})
        except ValueError as e:
            return Response({"success": False, "error": str(e)}, status=400)


class ApproveAllView(APIView):
    def post(self, request, query_id):
        doc = CompiledDocument.objects.get(query__query_id=query_id)
        data = ReviewManager().approve_all(doc.document_id)
        return Response({"success": True, "data": data})


class ResetReviewView(APIView):
    def post(self, request, query_id):
        doc = CompiledDocument.objects.get(query__query_id=query_id)
        data = ReviewManager().reset(doc.document_id)
        return Response({"success": True, "data": data})


class ExportStatusView(APIView):
    def get(self, request, query_id):
        doc = CompiledDocument.objects.get(query__query_id=query_id)
        items = doc.review_items
        return Response({"success": True, "data": {
            "can_export": doc.status == CompiledDocument.Status.REVIEW_COMPLETE,
            "review_completion_pct": doc.review_completion_pct,
            "blockers": {
                "pending_approvals": items.filter(is_null_field=False, is_approved=False).count(),
                "null_fields_unfilled": items.filter(is_null_field=True).count(),
            },
            "exports_available": {
                "pdf": {"available": bool(doc.export_pdf_path),
                        "generated_at": None},
                "docx": {"available": bool(doc.export_docx_path),
                         "generated_at": None},
            }
        }})


class ExportView(APIView):
    EXPORTERS = {"pdf": PDFExporter, "docx": DOCXExporter}
    MIME = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    def get(self, request, query_id, fmt):
        if fmt not in self.EXPORTERS:
            return Response({"success": False, "error": "Unsupported format"}, status=400)
        try:
            doc = CompiledDocument.objects.get(query__query_id=query_id)
            path = self.EXPORTERS[fmt]().export(doc.document_id)
            return FileResponse(open(path, "rb"), content_type=self.MIME[fmt],
                                as_attachment=True, filename=path.name)
        except ExportNotPermittedError as e:
            pending = doc.review_items.filter(is_null_field=False, is_approved=False).count()
            return Response({"success": False, "error": str(e),
                             "data": {"pending_approvals": pending}}, status=403)
