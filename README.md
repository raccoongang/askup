# Bridge for Adaptivity

## About

About the application

## Getting started

### Deployment

Deployment is based on the `Docker` containers. There are two configurations:
 `.dc-dev/docker-compose.yml` and `.dc-dev/docker-compose.yml` for development
and production purposes respectively.

Docker (17.12.0+) and Docker Compose (1.19.0+) are required to be installed before start
the deploying.

Clone project.

Before running deployment configure `secure.py` settings in the
`config/settings/` directory (see `secure.py.example`).

### Local deployment

Local deployment can be started by the docker-compose up command in the
console:

    [sudo] ./deploy-clean-dev.sh

Local deployment contains two containers:

- django -- container with the AskUp django application.

- postgresql -- container with the postgresql database.

  Note: Development server available on `localhost:8001`


### Running tests

You can run tests locally (directly on your host), or on the docker machine.

* to run tests locally:
    * install requirements with command `pip install -r requirements.txt`
    * run tests: `python manage.py test --settings config.settings.test` or
    just `pytest`. Both commands are equal.
* to run tests in docker container:
    * create docker container: `docker-compose -f docker-compose_local.yml up -d`
    * run tests: `docker exec -it django pytest`
        * if you see an error:
          ```
          import file mismatch:
          which is not the same as the test file we want to collect:
          config/settings/test.py
          HINT: remove __pycache__ / .pyc files and/or use a unique basename for your test file modules
          ```
          you should run: `find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf`
          and after that retry running the tests: `docker exec -it BFA_local pytest`


### Production deployment

Please ensure that file in `nginx/conf.d/askup.net.conf` exists and
is configured in proper way.

Run docker-compose up command with default `docker-compose.yml` file
to start production deployment:

    sudo docker-compose up -d

Production deployment contains three containers:

- django -- container with the AskUp django application.

- postgresql -- container with the postgresql database.

- nginx -- container with nginx server

### Additional notes

- if `requirements` changes were made containers rebuilding needed:

production:

    [sudo] docker-compose -f .dc-prod/docker-compose.yml build

stage:

    [sudo] docker-compose -f .dc-prod/docker-compose.yml build

development:

    [sudo] docker-compose -f .dc-dev/docker-compose.yml build
