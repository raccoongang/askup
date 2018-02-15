#!/bin/bash
source ~/.venvs/askup/bin/activate
export DJANGO_SETTINGS_MODULE="config.settings.dev"

while true;
do
    python manage.py runserver 0.0.0.0:8001
    sleep 1;
done
