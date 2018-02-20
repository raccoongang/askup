#!/bin/bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py loaddata askup/fixtures/groups.json

[[ "$ASKUPENV" =~ (dev|test) ]] && 
    psql -c "CREATE DATABASE travis_test_db;" -U postgres -h postgres &&
    psql -c "CREATE USER test PASSWORD 'pass';" -U postgres -h postgres &&
    psql -c "ALTER USER test CREATEDB;" -U postgres -h postgres &&
    psql -c "GRANT ALL PRIVILEGES on DATABASE travis_test_db to test;" -U postgres -h postgres

if [[ "$LOADMOCKUPDATA" ]]
then
    python manage.py loaddata askup/fixtures/mockup_data.json
fi
