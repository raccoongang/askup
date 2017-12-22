#!/bin/bash
[[ -e '/code/.initiated' ]] && exit 0

touch /code/.initiated
python manage.py migrate
python manage.py loaddata askup/fixtures/groups.json
[[ "$MOCKUPDATA" ]] && python manage.py loaddata askup/fixtures/mockup_data.json
