from pathlib import Path
from uuid import UUID
from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from .base import BaseExporter
from ..models import CompiledDocument, ReviewChecklistItem


class PDFExporter(BaseExporter):
    def export(self, document_id: UUID) -> Path:
        doc = CompiledDocument.objects.get(document_id=document_id)
        self._check_permission(doc)

        if doc.export_pdf_path:
            p = Path(doc.export_pdf_path)
            if p.exists():
                return p

        out_dir = Path(settings.EXPORT_ROOT) / str(document_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{document_id}.pdf"

        styles = getSampleStyleSheet()
        citation_style = ParagraphStyle("citation", parent=styles["Normal"],
                                        textColor=colors.grey, fontSize=8)
        flag_style = ParagraphStyle("flag", parent=styles["Normal"],
                                    textColor=colors.orange)
        null_style = ParagraphStyle("null", parent=styles["Normal"],
                                    textColor=colors.red, fontName="Helvetica-Bold")

        flowables = [
            Paragraph("LexAI — AI-Assisted Legal Document", styles["Title"]),
            Paragraph(f"Template: {doc.template_name or 'Analysis'}", styles["Normal"]),
            Paragraph(f"Verification Score: {doc.review_completion_pct:.0f}%", styles["Normal"]),
            Spacer(1, 20),
        ]

        for item in ReviewChecklistItem.objects.filter(document=doc).order_by("clause_index"):
            if item.is_null_field:
                flowables.append(Paragraph(
                    f"{item.clause_text} [REQUIRED — FILL BEFORE FILING]", null_style))
            else:
                flowables.append(Paragraph(item.clause_text, styles["Normal"]))
                if item.citation_string:
                    flowables.append(Paragraph(item.citation_string, citation_style))
                if item.verification_verdict == "INSUFFICIENT":
                    flowables.append(Paragraph("⚠ Verify manually", flag_style))
            flowables.append(Spacer(1, 8))

        flowables.append(Spacer(1, 30))
        flowables.append(Paragraph(
            "AI-assisted document. Review all flagged content before filing.",
            ParagraphStyle("disclaimer", parent=styles["Normal"],
                           textColor=colors.grey, fontSize=8, italics=1)
        ))

        pdf = SimpleDocTemplate(str(out_path), pagesize=A4)
        pdf.build(flowables)
        doc.export_pdf_path = str(out_path)
        doc.save(update_fields=["export_pdf_path"])
        return out_path
