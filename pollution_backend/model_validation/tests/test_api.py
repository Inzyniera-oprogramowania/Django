import pytest
from unittest.mock import patch
from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from pollution_backend.model_validation.models import ModelValidationRun
from pollution_backend.users.models import User


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email='other@example.com',
        password='testpass123'
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def validation_run(db, user):
    return ModelValidationRun.objects.create(
        user=user,
        name='Test Run',
        model_name='lstm_v1',
        data_start_time=timezone.now() - timedelta(days=7),
        data_end_time=timezone.now()
    )


@pytest.fixture
def other_user_validation_run(db, other_user):
    return ModelValidationRun.objects.create(
        user=other_user,
        name='Other Run',
        model_name='lstm_v1',
        data_start_time=timezone.now() - timedelta(days=7),
        data_end_time=timezone.now()
    )


class TestTriggerValidationView:

    @pytest.fixture
    def valid_payload(self):
        return {
            'run_name': 'benchmark_test'
        }

    def test_trigger_validation_unauthenticated(self, api_client, valid_payload):
        response = api_client.post('/api/validation/generate/', valid_payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('pollution_backend.model_validation.api.views.invoke_validation_lambda')
    def test_trigger_validation_success(self, mock_lambda, authenticated_client, valid_payload):
        response = authenticated_client.post('/api/validation/generate/', valid_payload, format='json')

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'message' in response.data
        mock_lambda.assert_called_once()

    @patch('pollution_backend.model_validation.api.views.invoke_validation_lambda')
    def test_trigger_validation_empty_payload(self, mock_lambda, authenticated_client):
        response = authenticated_client.post('/api/validation/generate/', {}, format='json')

        assert response.status_code == status.HTTP_202_ACCEPTED
        mock_lambda.assert_called_once()

    @patch('pollution_backend.model_validation.api.views.invoke_validation_lambda')
    def test_trigger_validation_with_model_name(self, mock_lambda, authenticated_client):
        payload = {
            'model_name': 'lstm_v2',
            'run_name': 'test_run'
        }
        response = authenticated_client.post('/api/validation/generate/', payload, format='json')

        assert response.status_code == status.HTTP_202_ACCEPTED

    @patch('pollution_backend.model_validation.api.views.invoke_validation_lambda')
    def test_trigger_validation_lambda_failure(self, mock_lambda, authenticated_client, valid_payload):
        from pollution_backend.services.aws_lambda import LambdaInvocationError
        mock_lambda.side_effect = LambdaInvocationError('AWS Error')

        response = authenticated_client.post('/api/validation/generate/', valid_payload, format='json')

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert 'error' in response.data


class TestValidationRunListView:

    def test_list_validation_runs_unauthenticated(self, api_client):
        response = api_client.get('/api/validation/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_validation_runs_user_isolation(self, authenticated_client, validation_run, other_user_validation_run):
        response = authenticated_client.get('/api/validation/')

        assert response.status_code == status.HTTP_200_OK
        run_ids = [r['id'] for r in response.data['results']]
        assert validation_run.id in run_ids
        assert other_user_validation_run.id not in run_ids

    def test_list_validation_runs_ordering(self, authenticated_client, user):
        older = ModelValidationRun.objects.create(
            user=user,
            name='Older Run',
            model_name='lstm_v1',
            data_start_time=timezone.now() - timedelta(days=14),
            data_end_time=timezone.now() - timedelta(days=7)
        )
        newer = ModelValidationRun.objects.create(
            user=user,
            name='Newer Run',
            model_name='lstm_v1',
            data_start_time=timezone.now() - timedelta(days=7),
            data_end_time=timezone.now()
        )

        response = authenticated_client.get('/api/validation/')

        assert response.status_code == status.HTTP_200_OK
        ids = [r['id'] for r in response.data['results']]
        assert ids.index(newer.id) < ids.index(older.id)


class TestValidationRunDetailView:

    def test_get_validation_detail_unauthenticated(self, api_client, validation_run):
        response = api_client.get(f'/api/validation/{validation_run.id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_validation_detail_success(self, authenticated_client, validation_run):
        response = authenticated_client.get(f'/api/validation/{validation_run.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == validation_run.id
        assert 'metrics' in response.data
        assert 'error_logs' in response.data

    def test_get_validation_detail_not_found(self, authenticated_client):
        response = authenticated_client.get('/api/validation/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_validation_detail_user_isolation(self, authenticated_client, other_user_validation_run):
        response = authenticated_client.get(f'/api/validation/{other_user_validation_run.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND
