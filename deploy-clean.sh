#!/bin/bash
if [[ "$1" == "" ]]
then
    DCENV="dev"
else
    DCENV="$1"
fi

ASKUP_REPO_PATH=`dirname $(readlink -f $0)`
cd $ASKUP_REPO_PATH/.dc-$DCENV &&
    docker-compose down &&
    rm -rf .volumes &&
    docker-compose build && docker-compose up -d
