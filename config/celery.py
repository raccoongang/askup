from celery import Celery

app = Celery(
    'config',
    broker='amqp://rabbitmq:rabbitmq@rabbitmq:5672//',
    backend='amqp://rabbitmq:rabbitmq@rabbitmq:5672//',
    include=['askup.tasks']
)

# Optional configuration, see the application user guide.
app.conf.update(result_expires=3600)

if __name__ == '__main__':
    app.start()
