import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "q4s_connect.settings")

app = Celery("q4s_connect")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
