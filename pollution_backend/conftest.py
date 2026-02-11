import pytest

from pollution_backend.users.models import User
from pollution_backend.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture(scope='session')
def django_db_setup():
    pass


@pytest.fixture
def user(db) -> User:
    return UserFactory()
