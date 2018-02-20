#!/bin/bash
sed 's#localhost#postgres#g' -i config/settings/test.py
docker exec -it askupdev_django_1 python /askup/manage.py test
sed 's#postgres#localhost#g' -i config/settings/test.py
