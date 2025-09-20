"""
Celery configuration for background task processing
"""
import os
from celery import Celery

# Get Redis URL from environment (prioritize public URL)
redis_url = os.getenv("REDIS_PUBLIC_URL") or os.getenv("REDIS_URL")

# Create Celery app
app = Celery('linkedin_content_generator')

# Configure Celery
app.conf.update(
    broker_url=redis_url,
    result_backend=redis_url,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    # Task routing
    task_routes={
        'celery_app.create_post_task': {'queue': 'ai_processing'},
        'celery_app.format_with_feedback_task': {'queue': 'ai_processing'},
        'celery_app.format_with_template_task': {'queue': 'ai_processing'},
    },
    # Task execution settings
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Result settings
    result_expires=3600,  # 1 hour
    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Import tasks (will be defined in tasks.py)
from tasks import *

if __name__ == '__main__':
    app.start()
