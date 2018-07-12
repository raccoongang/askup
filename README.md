# AskUp

## About

Educational project to help the students, graduates and professionals to consolidate a knowledge on their subjects or the subjects of organizations they are belong to.

### Deployment

Deployment is based on the `Docker` containers. There are two configurations:
`.dc-dev/docker-compose.yml` and `.dc-dev/docker-compose.yml` for the development/testing
and the staging/production purposes respectively.
Project containers configuration consists of the five containers:
- django -- container with the AskUp django application.
- celery_worker -- celery worker duplicate of the django container.
- celery_beat -- celery beat duplicate of the django container.
- postgresql -- container with the postgresql database.
- nginx -- container with the nginx as reverse proxy frontend and static files provider

To fully deploy the project folow the steps below:
1. Install prerequizites on your machine:
 - Docker (17.12.0+)
 - Docker Compose (1.19.0+)
2. Clone the project
3. Prepare the secure.py with your SMTP credentials and the secret key and put it in the `<repo_ dir>/config/settings` (see `<repo_ dir>/config/settings/secure_example.py`)
4. go into desired environment container directory ( `<repo_ dir>/.dc-dev` or `<repo_ dir>/.dc-prod`)
5. run `sudo ./deploy-clean.sh env_name` where *env_name* is `dev` or `prod`
6. after successful build run `sudo docker-compose up -d`


### Running tests

Tests are running inside the docker container.

To run them
1. Deploy the project under the *dev* or the *prod* environment
2. Run tests:
`[sudo] docker exec -it django_container python manage.py test`


### Production deployment

Run docker-compose up command with default `docker-compose.yml` file
to start production deployment:
`sudo docker-compose up -d`
