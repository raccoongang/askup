from celery.schedules import crontab
from celery.task import periodic_task
from django.conf import settings

from askup.utils.general import send_subscription_emails


if 'SUBSCRIPTION_SCHEDULE' in dir(settings):
    subscription_schedule = settings.SUBSCRIPTION_SCHEDULE
else:
    subscription_schedule = {'hour': 9, 'minute': 0, 'day_of_week': 4}


@periodic_task(run_every=crontab(**subscription_schedule))
def do_send_subscriptions_emails():
    """
    Send scheduled quizzes.
    """
    send_subscription_emails()
