from celery.schedules import crontab
from celery.task import periodic_task

from askup.utils.general import send_subscription_quizzes


@periodic_task(run_every=crontab(hour=11, minute=10, day_of_week='*'))
def do_send_subscriptions_quizzes():
    """
    Send scheduled quizzes.
    """
    send_subscription_quizzes()
