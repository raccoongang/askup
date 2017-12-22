FROM python:3.6

MAINTAINER Michael Khaimov <khaimovmr@gmail.com>

RUN apt-get update && apt-get install -y postgresql-client netcat
RUN mkdir /code
COPY . /code
WORKDIR /code
RUN pip install -r requirements.txt

VOLUME /var/log

EXPOSE 8001

cmd until nc -w 3 postgres 5432; do sleep 1; done && /code/init-prod-env.sh && python manage.py runserver 0.0.0.0:8001
