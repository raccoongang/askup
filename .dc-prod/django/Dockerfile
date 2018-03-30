FROM python:3.6

MAINTAINER Michael Khaimov <khaimovmr@gmail.com>

ENV LOADMOCKUPDATA $LOADMOCKUPDATA
RUN apt-get update && apt-get install -y postgresql-client netcat

WORKDIR /askup
COPY requirements.txt /askup/requirements.txt
RUN pip install -r requirements.txt

VOLUME /var/log
VOLUME /askup

EXPOSE 8001

cmd echo "Starting the entrypoint..." && while [ $(nc -w 1 -z -v postgres 5432 2>&1 | grep -o 'refused') ]; do echo "Trying to connect to the postgres...\n"; sleep 1; done && /askup/init-django.sh && /askup/start-server.sh
