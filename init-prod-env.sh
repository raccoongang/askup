#!/bin/bash
[[ -e '/.initiated' ]] && exit 0

touch /.initiated
python manage.py migrate
python manage.py loaddata askup/fixtures/groups.json
python manage.py collectstatic --noinput
[[ "$MOCKUPDATA" ]] && python manage.py loaddata askup/fixtures/mockup_data.json
