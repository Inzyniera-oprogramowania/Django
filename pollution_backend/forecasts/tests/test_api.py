import pytest
from unittest.mock import patch
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from pollution_backend.forecasts.models import Forecast, ForecastArea, ForecastPollutant
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
def forecast_area(db):
    return ForecastArea.objects.create(
        name='Kraków',
        h3_cells=['8a283082a677fff']
    )


@pytest.fixture
def forecast(db, user, forecast_area):
    return Forecast.objects.create(
        user=user,
        forecast_area=forecast_area,
        time_horizon={'hours': 24}
    )


@pytest.fixture
def other_user_forecast(db, other_user, forecast_area):
    return Forecast.objects.create(
        user=other_user,
        forecast_area=forecast_area,
        time_horizon={'hours': 24}
    )


class TestTriggerForecastView:

    @pytest.fixture
    def valid_payload(self):
        return {
            'h3_index': '8a283082a677fff',
            'pollutants': ['PM2.5', 'NO2']
        }

    def test_trigger_forecast_unauthenticated(self, api_client, valid_payload):
        response = api_client.post('/api/forecast/generate/', valid_payload, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch('pollution_backend.forecasts.api.views.invoke_forecast_lambda')
    def test_trigger_forecast_success(self, mock_lambda, authenticated_client, valid_payload):
        response = authenticated_client.post('/api/forecast/generate/', valid_payload, format='json')

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'message' in response.data
        mock_lambda.assert_called_once()

    def test_trigger_forecast_invalid_h3_index_too_short(self, authenticated_client):
        payload = {
            'h3_index': 'abc',
            'pollutants': ['PM2.5']
        }
        response = authenticated_client.post('/api/forecast/generate/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_trigger_forecast_invalid_h3_index_too_long(self, authenticated_client):
        payload = {
            'h3_index': 'a' * 20,
            'pollutants': ['PM2.5']
        }
        response = authenticated_client.post('/api/forecast/generate/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_trigger_forecast_empty_pollutants(self, authenticated_client):
        payload = {
            'h3_index': '8a283082a677fff',
            'pollutants': []
        }
        response = authenticated_client.post('/api/forecast/generate/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch('pollution_backend.forecasts.api.views.invoke_forecast_lambda')
    def test_trigger_forecast_lambda_failure(self, mock_lambda, authenticated_client, valid_payload):
        from pollution_backend.services.aws_lambda import LambdaInvocationError
        mock_lambda.side_effect = LambdaInvocationError('AWS Error')

        response = authenticated_client.post('/api/forecast/generate/', valid_payload, format='json')

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert 'error' in response.data


class TestForecastListView:

    def test_list_forecasts_user_isolation(self, authenticated_client, forecast, other_user_forecast):
        response = authenticated_client.get('/api/forecast/')

        assert response.status_code == status.HTTP_200_OK
        forecast_ids = [f['id'] for f in response.data['results']]
        assert forecast.id in forecast_ids
        assert other_user_forecast.id not in forecast_ids

    def test_list_forecasts_ordering(self, authenticated_client, user, forecast_area):
        older = Forecast.objects.create(
            user=user,
            forecast_area=forecast_area,
            time_horizon={'hours': 12}
        )
        newer = Forecast.objects.create(
            user=user,
            forecast_area=forecast_area,
            time_horizon={'hours': 24}
        )

        response = authenticated_client.get('/api/forecast/')

        assert response.status_code == status.HTTP_200_OK
        ids = [f['id'] for f in response.data['results']]
        assert ids.index(newer.id) < ids.index(older.id)


class TestForecastDetailView:

    def test_get_forecast_detail_success(self, authenticated_client, forecast):
        response = authenticated_client.get(f'/api/forecast/{forecast.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == forecast.id
        assert 'pollutant_data' in response.data

    def test_get_forecast_detail_not_found(self, authenticated_client):
        response = authenticated_client.get('/api/forecast/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_get_forecast_detail_user_isolation(self, authenticated_client, other_user_forecast):
        response = authenticated_client.get(f'/api/forecast/{other_user_forecast.id}/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestForecastAreaListView:

    def test_list_areas_success(self, authenticated_client, forecast_area):
        response = authenticated_client.get('/api/forecast/areas/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

    def test_list_areas_ordering(self, authenticated_client, db):
        ForecastArea.objects.create(name='Wrocław', h3_cells=[])
        ForecastArea.objects.create(name='Gdańsk', h3_cells=[])

        response = authenticated_client.get('/api/forecast/areas/')

        names = [area['name'] for area in response.data]
        assert names == sorted(names)
