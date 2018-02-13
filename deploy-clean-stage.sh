#!/bin/bash
ASKUP_REPO_PATH=`dirname $(readlink -f $0)`
$ASKUP_REPO_PATH/deploy-clean.sh prod
