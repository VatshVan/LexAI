from django.urls import path

from apps.templates_engine import views

urlpatterns = [
    path("templates/", views.TemplateListView.as_view()),
    path("templates/<str:template_name>/", views.TemplateDetailView.as_view()),
]
