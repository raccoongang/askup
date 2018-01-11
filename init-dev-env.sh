#!/bin/bash
read -s -p "Please enter your PostgreSQL password: " PGPASSWORD
export PGPASSWORD
export DJANGO_SETTINGS_MODULE='config.settings.dev'
[[ "$(which psql)" == "" ]] &&
	echo "Inslatting postgresql-client... \n" &&
       	sudo apt-get install -y postgresql-client &&
       	echo "\n"
[[ ! -e ~/.venvs/askup ]] &&
       	echo "Creating the environment... \n" &&
       	virtualenv -p python3.6 ~/.venvs/askup --prompt="(askup) " &&
       	echo "\n"
psql -w -h postgres -U postgres -tc "select 1 from pg_database where datname = 'askup'" |
	grep -q 1 ||
	psql -w -h postgres -U postgres -c 'create database askup'
source ~/.venvs/askup/bin/activate
pip install -r ./requirements.txt
python manage.py migrate
python manage.py loaddata askup/fixtures/groups.json
python manage.py loaddata askup/fixtures/mockup_data.json
