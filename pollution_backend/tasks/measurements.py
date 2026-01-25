from config import celery_app
from pollution_backend.services.measurements import MeasurementImportService

@celery_app.task
def import_measurements_task(data: list, user_id: int | None, api_key_id: int | None):
    MeasurementImportService.process_batch(data, user_id, api_key_id)
