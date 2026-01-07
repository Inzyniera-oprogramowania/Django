import pytest
from rest_framework.test import APIRequestFactory

from pollution_backend.users.api.views import UserViewSet
from pollution_backend.users.models import User


class TestUserViewSet:
    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_get_queryset(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        response = view.me(request)  # type: ignore[call-arg, arg-type, misc]

        assert response.data == {
            "id": user.id,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_active": user.is_active,
            "date_joined": user.date_joined,
        }
