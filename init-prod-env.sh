#!/bin/bash
[[ -e '/.initiated' ]] && exit 0

touch /.initiated
python manage.py migrate
python manage.py loaddata askup/fixtures/groups.json
[[ "$MOCKUPDATA" ]] && python manage.py loaddata askup/fixtures/mockup_data.json
