import pytest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError

from pollution_backend.services.aws_lambda import (
    invoke_forecast_lambda,
    invoke_validation_lambda,
    LambdaInvocationError
)


@pytest.fixture
def mock_boto_client():
    with patch('pollution_backend.services.aws_lambda.boto3.client') as mock:
        yield mock


@pytest.fixture
def mock_settings(settings):
    settings.AWS_REGION_NAME = 'eu-central-1'
    settings.AWS_ACCESS_KEY_ID = 'test-access-key'
    settings.AWS_SECRET_ACCESS_KEY = 'test-secret-key'
    settings.FORECAST_LAMBDA_FUNCTION_NAME = 'forecast-lambda'
    settings.VALIDATION_LAMBDA_FUNCTION_NAME = 'validation-lambda'
    return settings


class TestInvokeForecastLambda:

    def test_invoke_forecast_lambda_success(self, mock_boto_client, mock_settings):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda

        invoke_forecast_lambda(
            user_id=1,
            h3_index='8a283082a677fff',
            pollutants=['PM2.5', 'NO2']
        )

        mock_lambda.invoke.assert_called_once()

    def test_invoke_forecast_lambda_wrong_status_code(self, mock_boto_client, mock_settings):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 500}
        mock_boto_client.return_value = mock_lambda

        with pytest.raises(LambdaInvocationError):
            invoke_forecast_lambda(
                user_id=1,
                h3_index='8a283082a677fff',
                pollutants=['PM2.5']
            )

    def test_invoke_forecast_lambda_boto_exception(self, mock_boto_client, mock_settings):
        mock_lambda = MagicMock()
        mock_lambda.invoke.side_effect = ClientError(
            {'Error': {'Code': 'ServiceException', 'Message': 'Service error'}},
            'Invoke'
        )
        mock_boto_client.return_value = mock_lambda

        with pytest.raises(LambdaInvocationError) as exc_info:
            invoke_forecast_lambda(
                user_id=1,
                h3_index='8a283082a677fff',
                pollutants=['PM2.5']
            )

        assert 'AWS Error' in str(exc_info.value)

    def test_invoke_forecast_lambda_payload_structure(self, mock_boto_client, mock_settings):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda

        invoke_forecast_lambda(
            user_id=42,
            h3_index='8a283082a677fff',
            pollutants=['PM2.5', 'O3'],
            model_name='lstm_v2'
        )

        call_kwargs = mock_lambda.invoke.call_args[1]
        import json
        payload = json.loads(call_kwargs['Payload'])

        assert payload['user_id'] == 42
        assert payload['h3_index'] == '8a283082a677fff'
        assert payload['pollutants'] == ['PM2.5', 'O3']
        assert payload['model_name'] == 'lstm_v2'

    def test_invoke_forecast_lambda_optional_model_name(self, mock_boto_client, mock_settings):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda

        invoke_forecast_lambda(
            user_id=1,
            h3_index='8a283082a677fff',
            pollutants=['PM2.5']
        )

        call_kwargs = mock_lambda.invoke.call_args[1]
        import json
        payload = json.loads(call_kwargs['Payload'])

        assert payload['model_name'] is None


class TestInvokeValidationLambda:

    def test_invoke_validation_lambda_success(self, mock_boto_client, mock_settings):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 202}
        mock_boto_client.return_value = mock_lambda

        invoke_validation_lambda(user_id=1, run_name='test_run')

        mock_lambda.invoke.assert_called_once()

    def test_invoke_validation_lambda_failure(self, mock_boto_client, mock_settings):
        mock_lambda = MagicMock()
        mock_lambda.invoke.return_value = {'StatusCode': 500}
        mock_boto_client.return_value = mock_lambda

        with pytest.raises(LambdaInvocationError):
            invoke_validation_lambda(user_id=1, run_name='test_run')
