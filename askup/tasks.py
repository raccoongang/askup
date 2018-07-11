from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings

from askup.utils.general import send_subscription_emails


@periodic_task(run_every=crontab(**settings.SUBSCRIPTION_SCHEDULE))
def do_send_subscriptions_emails():
    """
    Send scheduled quizzes.
    """
    send_subscription_emails()
