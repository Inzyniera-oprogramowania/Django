from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from pollution_backend.users.api.views import UserViewSet, ApiKeyViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("api-keys", ApiKeyViewSet, basename="api-keys")


app_name = "api"
urlpatterns = router.urls
