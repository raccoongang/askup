#!/bin/bash
export PGPASSWORD='pass'
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

psql -c "CREATE DATABASE travis_test_db;" -U postgres -h postgres
psql -c "CREATE USER test PASSWORD 'pass';" -U postgres -h postgres
psql -c "ALTER USER test CREATEDB;" -U postgres -h postgres
psql -c "GRANT ALL PRIVILEGES on DATABASE travis_test_db to test;" -U postgres -h postgres

pip install -r ./requirements.txt
python manage.py migrate
python manage.py loaddata askup/fixtures/groups.json
python manage.py loaddata askup/fixtures/mockup_data.json
python manage.py collectstatic --noinput
