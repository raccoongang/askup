#!/bin/bash
if [[ "$1" == "" ]]
then
    DCENV="prod"
else
    DCENV="$1"
fi

ASKUP_REPO_PATH=`dirname $(readlink -f $0)`
cd $ASKUP_REPO_PATH/.dc-$DCENV
export MOCKUPDATA=1
docker-compose down
rm -rf .volumes
docker-compose build && docker-compose up -d
