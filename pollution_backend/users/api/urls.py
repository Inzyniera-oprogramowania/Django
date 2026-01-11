from rest_framework.routers import DefaultRouter

from pollution_backend.users.api.views import UserViewSet, InstitutionViewSet

app_name = "users"

router = DefaultRouter()
router.register("users", UserViewSet)
router.register("institutions", InstitutionViewSet)

urlpatterns = router.urls
