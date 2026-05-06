from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.documents.urls")),
    path("api/v1/", include("apps.orchestration.urls")),
    path("api/v1/", include("apps.templates_engine.urls")),
    path("api/v1/", include("apps.compilation.urls")),
]

if settings.SHOW_API_DOCS:
    urlpatterns += [
        path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
        path(
            "api/v1/schema/ui/",
            SpectacularSwaggerView.as_view(url_name="schema"),
        ),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
