# Pollution IoT

Backend for an IoT-based air pollution monitoring system. The platform collects real-time measurements from distributed sensor stations via MQTT, stores and analyzes pollutant data, and provides pollution forecasting powered by AWS Lambda.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

## Key Features

- **Real-time data ingestion** – MQTT listener receives measurements and device status from IoT sensors, with live updates via WebSockets (Django Channels)
- **Sensor & station management** – registration, health monitoring, and activity tracking of monitoring stations and their sensors
- **Anomaly detection** – configurable per-pollutant rules for threshold alerts and sudden-change detection
- **Pollution forecasting** – on-demand forecast generation delegated to AWS Lambda, with per-pollutant predicted values and uncertainty
- **Model validation & benchmarking** – trigger validation runs against historical data to evaluate forecast accuracy
- **Alerts & notifications** – quality-norm-based alerts sent to subscribed users
- **Reporting** – PDF report generation via ReportLab
- **REST API** – fully documented with Swagger / OpenAPI (drf-spectacular)

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 5.2 / Django REST Framework |
| Database | PostgreSQL 15 + PostGIS (geospatial support) |
| Real-time | MQTT (Eclipse Mosquitto) · Django Channels + Redis |
| Task queue | Celery + Celery Beat (periodic tasks) |
| Cloud | AWS Lambda (forecasting) · Boto3 |
| Auth | JWT (Simple JWT) · dj-rest-auth · django-allauth |
| Containerisation | Docker Compose (local & production) |
| Python tooling | uv · Ruff · mypy · pytest |

# Test Commands

### Send system log and measurements for sensor ID=2

**Device Status:**

```bash
python3 scripts/simulate_sensor.py --status --sensor-id 2 --station 1TEST-STATION --status-interval 3 --host localhost
```

**Measurements:**

```bash
python3 scripts/simulate_sensor.py --sensor-id 2 --station 1TEST-STATION --pollutant TEST --interval 5 --host localhost
```

### Station Heartbeat Simulation (Health Check)

```bash
python3 scripts/simulate_station.py --station 1TEST-STATION --interval 60 --host localhost
```

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      uv run python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    uv run mypy pollution_backend

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    uv run coverage run -m pytest
    uv run coverage html
    uv run open htmlcov/index.html

#### Running tests with pytest

    uv run pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

### Celery

This app comes with Celery.

To run a celery worker:

```bash
cd pollution_backend
uv run celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important _where_ the celery commands are run. If you are in the same folder with _manage.py_, you should be right.

To run [periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html), you'll need to start the celery beat scheduler service. You can start it as a standalone process:

```bash
cd pollution_backend
uv run celery -A config.celery_app beat
```

or you can embed the beat service inside a worker with the `-B` option (not recommended for production use):

```bash
cd pollution_backend
uv run celery -A config.celery_app worker -B -l info
```

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).
