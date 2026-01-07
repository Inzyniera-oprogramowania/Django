from rest_framework.routers import DefaultRouter

from pollution_backend.users.api.views import UserViewSet

app_name = "users"

router = DefaultRouter()
router.register("users", UserViewSet)

urlpatterns = router.urls
