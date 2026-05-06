from django.urls import path
from . import views

urlpatterns = [
    path("queries/<str:query_id>/document/", views.CompiledDocumentView.as_view()),
    path("queries/<str:query_id>/document/clauses/<int:clause_index>/approve/",
         views.ApproveClauseView.as_view()),
    path("queries/<str:query_id>/document/clauses/approve-all/",
         views.ApproveAllView.as_view()),
    path("queries/<str:query_id>/document/clauses/reset/",
         views.ResetReviewView.as_view()),
    path("queries/<str:query_id>/document/export/status/",
         views.ExportStatusView.as_view()),
    path("queries/<str:query_id>/document/export/<str:fmt>/",
         views.ExportView.as_view()),
]
