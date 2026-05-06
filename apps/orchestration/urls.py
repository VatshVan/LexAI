from django.urls import path
from . import views

urlpatterns = [
    path("queries/", views.SubmitQueryView.as_view()),
    path("queries/<str:query_id>/", views.QueryDetailView.as_view()),
    path("queries/<str:query_id>/stream/", views.QueryStreamView.as_view()),
    path("sessions/<str:session_id>/queries/", views.SessionQueriesView.as_view()),
]
