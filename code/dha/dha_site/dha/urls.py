from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from rest_framework.routers import DefaultRouter

from .views import InstanceViewSet

router = DefaultRouter()

instance_routes = router.register("instances", InstanceViewSet, basename="instances")

urlpatterns = [
     path('schema/', SpectacularAPIView.as_view(), name='schema'),  # JSON schema
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # Swagger UI
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),  # Redoc UI
]

urlpatterns += router.urls