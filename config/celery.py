from celery import Celery

app = Celery('config')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

if __name__ == '__main__':
    app.start()
