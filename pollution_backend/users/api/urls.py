from rest_framework.routers import DefaultRouter

from pollution_backend.users.api.views import UserViewSet, InstitutionViewSet, ApiKeyViewSet

app_name = "users"

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("institutions", InstitutionViewSet)
router.register(r'api-keys', ApiKeyViewSet, basename='api-keys')

urlpatterns = router.urls
