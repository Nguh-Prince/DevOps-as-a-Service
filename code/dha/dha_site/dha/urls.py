from rest_framework.routers import DefaultRouter

from .views import InstanceViewSet

router = DefaultRouter()

instance_routes = router.register("instances", InstanceViewSet, basename="instances")

urlpatterns = router.urls