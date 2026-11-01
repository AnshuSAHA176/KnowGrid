from celery import shared_task
from apps.ytvideo.dispacher import dispacher


@shared_task
def dispatch_outbox_events():
    dispacher()