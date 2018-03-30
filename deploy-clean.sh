#!/bin/bash
if [[ "$1" == "" ]]
then
    DCENV="dev"
else
    DCENV="$1"
fi

REPO_DIR=`dirname $(realpath $0)`
COMPOSE_DIR=$REPO_DIR/.dc-$DCENV
cd $COMPOSE_DIR

[[ $? != 0 ]] && echo "Such environment isn't defined" && exit 1

docker-compose down
sudo rm -rf $COMPOSE_DIR/.volumes
sudo rm -rf $REPO_DIR/.initialized
sudo docker-compose build && docker-compose up -d

if [[ "$DCENV" == "dev" ]]
then
    docker-compose logs -f
fi
