#!/bin/bash

# 1: fab target
# 2: username
# 3: ssh key path
# 4: hostname
# 5: chefroles file

cd `dirname $0`/fab-bootstrap

CMD="fab -D -u $2 -i $3  $1:hosts=$4,rolesfile=$5"
echo "Running command: $CMD"

$CMD
exit $?
