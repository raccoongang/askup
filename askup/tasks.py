from celery.schedules import crontab
from celery.task import periodic_task

from askup.utils.general import send_subscription_emails


@periodic_task(run_every=crontab(hour='9', minute='0', day_of_week='4'))
def do_send_subscriptions_emails():
    """
    Send scheduled quizzes.
    """
    send_subscription_emails()
