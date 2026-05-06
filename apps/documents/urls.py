"""
LexAI document URL configuration.
"""
from django.urls import path

from apps.documents.views import (
    DocumentDeleteView,
    DocumentDetailView,
    DocumentStatusView,
    DocumentUploadView,
    SessionCreateView,
    SessionDeleteView,
    SessionDocumentsView,
    SessionStatsView,
)

app_name = "documents"

urlpatterns = [
    path("sessions/", SessionCreateView.as_view(), name="session-create"),
    path("documents/upload/", DocumentUploadView.as_view(), name="document-upload"),
    path(
        "documents/<uuid:document_id>/status/",
        DocumentStatusView.as_view(),
        name="document-status",
    ),
    path(
        "documents/<uuid:document_id>/",
        DocumentDetailView.as_view(),
        name="document-detail",
    ),
    path(
        "documents/<uuid:document_id>/delete/",
        DocumentDeleteView.as_view(),
        name="document-delete",
    ),
    path(
        "sessions/<uuid:session_id>/documents/",
        SessionDocumentsView.as_view(),
        name="session-documents",
    ),
    path(
        "sessions/<uuid:session_id>/stats/",
        SessionStatsView.as_view(),
        name="session-stats",
    ),
    path(
        "sessions/<uuid:session_id>/",
        SessionDeleteView.as_view(),
        name="session-delete",
    ),
]
