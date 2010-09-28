#!/bin/bash

PYTHON_EXE="/usr/bin/env python"

# -----------------------------------------------------------------------------

HELP_MESSAGE="This program (with no arguments) checks on basic prerequisites for running epumgmt."
if [ "X$1" == "X-h" ] || [ "X$1" == "X-help" ] || [ "X$1" == "X--help" ] || [ "X$1" == "Xhelp" ]; then
    echo -e "$HELP_MESSAGE"
    exit 1
fi

# -----------------------------------------------------------------------------

NIMBUS_CONTROL_DIR_REL="`dirname $0`/.."
NIMBUS_CONTROL_DIR=`cd $NIMBUS_CONTROL_DIR_REL; pwd`
NIMBUS_CONTROL_PYLIB="$NIMBUS_CONTROL_DIR/lib/python"
NIMBUS_CONTROL_PYSRC="$NIMBUS_CONTROL_DIR/src/python"
PYTHONPATH="$NIMBUS_CONTROL_PYSRC:$NIMBUS_CONTROL_PYLIB:$PYTHONPATH"
export PYTHONPATH

# -----------------------------------------------------------------------------

$PYTHON_EXE $NIMBUS_CONTROL_PYSRC/epumgmt/sbin/check_dependencies.py $CONFSTRING

