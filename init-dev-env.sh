#!/bin/bash

read -s -p "Please enter your PostgreSQL password: " PGPASSWORD
export PGPASSWORD
[[ "$(which psql)" == "" ]] && echo "Inslatting postgresql-client... \n" && sudo apt-get install postgresql-client && echo "\n"
[[ ! -e ./.venv ]] && echo "Creating the environment... \n" && virtualenv -p python3.6 .venv --prompt="(askup) " && echo "\n"
psql -w -h postgres -U postgres -tc "select 1 from pg_database where datname = 'askup'" | grep -q 1 || psql -w -h postgres -U postgres -c 'create database askup'
source ./.venv/bin/activate
pip install -r ./requirements.txt
python manage.py createsuperuser --noinput --username admin --email admin@admin.org
