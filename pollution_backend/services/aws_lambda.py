import json
import logging

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)


class LambdaInvocationError(Exception):
    pass


def invoke_forecast_lambda(user_id, h3_index, pollutants, model_name=None):
    payload_data = {
        "user_id": user_id,
        "h3_index": h3_index,
        "pollutants": pollutants,
        "model_name": model_name
    }

    client = boto3.client(
        'lambda',
        region_name=settings.AWS_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    try:
        response = client.invoke(
            FunctionName=settings.FORECAST_LAMBDA_FUNCTION_NAME,
            InvocationType='Event',
            Payload=json.dumps(payload_data)
        )

        if response['StatusCode'] != 202:
            logger.error(f"Lambda returned unexpected status code: {response['StatusCode']}")
            raise LambdaInvocationError("Failed to trigger forecast generation.")

        logger.info(f"Successfully triggered forecast lambda for user {user_id}")

    except Exception as e:
        logger.exception("Error invoking Lambda function")
        raise LambdaInvocationError(f"AWS Error: {str(e)}")


def invoke_validation_lambda(user_id, model_name=None, run_name=None):
    payload_data = {
        "user_id": user_id,
        "model_name": model_name,
        "run_name": run_name
    }

    client = boto3.client(
        'lambda',
        region_name=settings.AWS_REGION_NAME,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
    )

    try:
        response = client.invoke(
            FunctionName=settings.VALIDATION_LAMBDA_FUNCTION_NAME,
            InvocationType='Event',
            Payload=json.dumps(payload_data)
        )

        if response['StatusCode'] != 202:
            logger.error(f"Validation Lambda returned unexpected status code: {response['StatusCode']}")
            raise LambdaInvocationError("Failed to trigger validation run.")

        logger.info(f"Successfully triggered validation lambda for user {user_id}")

    except Exception as e:
        logger.exception("Error invoking Validation Lambda function")
        raise LambdaInvocationError(f"AWS Error: {str(e)}")
