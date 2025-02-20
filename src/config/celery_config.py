from celery import Celery

celery_app = Celery(
    'weaver',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/1'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    broker_connection_retry_on_startup=True
)

celery_app.autodiscover_tasks(['src.modules.GLaDOS','src.modules.Veda'], related_name='tasks')

