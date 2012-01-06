#!/bin/bash

PYTHON_EXE="/usr/bin/env python"

NIMBUS_CONTROL_DIR_REL="`dirname $0`/.."
NIMBUS_CONTROL_DIR=`cd $NIMBUS_CONTROL_DIR_REL; pwd`

default_dbfile="$NIMBUS_CONTROL_DIR/var/epumgmt/persistence/epumgmt.db"
if [ ! -f $default_dbfile ]; then
    touch $default_dbfile
fi

NIMBUS_CONTROL_MAINCONF="$NIMBUS_CONTROL_DIR/etc/epumgmt/main.conf"

needsconf="y"
for i in "$@"; do
  if [ "--conf" == "$i" ]; then
    needsconf="n"
  fi
  if [ "-c" == "$i" ]; then
    needsconf="n"
  fi
done

CONFSTRING=""
if [ "X$needsconf" == "Xy" ]; then
  if [ ! -f "$NIMBUS_CONTROL_MAINCONF" ]; then
    echo ""
    echo "Cannot find main conf file, exiting. (expected at '$NIMBUS_CONTROL_MAINCONF')"
    exit 1
  fi
  CONFSTRING="--conf $NIMBUS_CONTROL_MAINCONF"
fi


PYTHONPATH=".:$NIMBUS_CONTROL_PYSRC:$NIMBUS_CONTROL_PYLIB:$PYTHONPATH"
export PYTHONPATH

# -----------------------------------------------------------------------------

echo $PYTHON_EXE $NIMBUS_CONTROL_DIR/epumgmt/main/em_cmdline.py $CONFSTRING $@
$PYTHON_EXE $NIMBUS_CONTROL_DIR/epumgmt/main/em_cmdline.py $CONFSTRING $@
