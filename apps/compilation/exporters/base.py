from abc import ABC, abstractmethod
from pathlib import Path
from uuid import UUID
from ..models import CompiledDocument


class ExportNotPermittedError(Exception): pass


class BaseExporter(ABC):
    def _check_permission(self, doc: CompiledDocument):
        if doc.status != CompiledDocument.Status.REVIEW_COMPLETE:
            pending = doc.total_clauses - doc.approved_clauses
            raise ExportNotPermittedError(
                f"Export blocked: {pending} clause(s) pending approval."
            )

    @abstractmethod
    def export(self, document_id: UUID) -> Path: ...
