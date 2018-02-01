#!/bin/bash
ASKUP_REPO_PATH=`dirname $(readlink -f $0)`
cd $ASKUP_REPO_PATH/.dc-prod
export MOCKUPDATA=1
docker-compose down
rm -rf .volumes
docker-compose build && docker-compose up -d
