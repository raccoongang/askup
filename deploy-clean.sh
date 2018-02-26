#!/bin/bash
if [[ "$1" == "" ]]
then
    DCENV="dev"
else
    DCENV="$1"
fi

COMPOSE_DIR=`dirname $(realpath $0)`/.dc-$DCENV
cd $COMPOSE_DIR

[[ $? != 0 ]] && echo "Such environment isn't defined" && exit 1

docker-compose down
sudo rm -rf $COMPOSE_DIR/.volumes
sudo docker-compose build && docker-compose up -d
