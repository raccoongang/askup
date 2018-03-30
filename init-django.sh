#!/bin/bash

# Run the initiation below only at the first container run
echo "Checking if the environment was initialized before..."
[[ -e /askup/.initialized ]] && exit
echo "Starting the environment initialization process."
touch /askup/.initialized

python manage.py createcachetable
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

echo "Environment was successfuly initiated."
