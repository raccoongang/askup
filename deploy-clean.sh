#!/bin/bash
if [[ "$1" == "" ]]
then
    DCENV="dev"
else
    DCENV="$1"
fi

cd `dirname $(readlink -f $0)`/.dc-$DCENV

[[ $? != 0 ]] && echo "Such environment isn't defined" && exit 1

docker-compose down
sudo rm -rf .volumes
sudo docker-compose build && sudo docker-compose up -d
