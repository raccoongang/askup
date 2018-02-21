#!/bin/bash
if [[ "$1" == "" ]]
then
    DCENV="dev"
else
    DCENV="$1"
fi

docker-compose down
cd `dirname $(readlink -f $0)`/.dc-$DCENV &&
    sudo rm -rf .volumes &&
    sudo docker-compose build &&
    sudo docker-compose up -d
