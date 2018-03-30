#!/bin/bash
if [[ "$ASKUPENV" =~ (dev|test) ]]
then
    while true
    do
        echo "Running the runserver for a dev purposes..."
        python manage.py runserver 0.0.0.0:8001
        sleep 5
    done
else
    while true
    do
        echo "Running the gunicorn application server..."
        gunicorn config.wsgi:application -w 2 -b :8001 --log-level=info
        sleep 5
    done
fi
