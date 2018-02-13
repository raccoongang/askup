#!/bin/bash
ASKUP_REPO_PATH=`dirname $(readlink -f $0)`
$ASKUP_REPO_PATH/deploy-clean.sh dev
$ASKUP_REPO_PATH/init-dev-env.sh
