#!/usr/bin/env python

# We will have to make something that can automically determine a list of EPU
# controllers to wait for in each level.  For now, hardcoding the name here.

CONTROLLER="epu_controller_sleeper1"
CONTROLLER2="epu_controller_sleeper2"

APP_DIR="/home/controllers/app"

MESSAGING_CONF="/home/ubuntu/messaging.conf"
VENV_PYTHON="sudo /home/controllers/app-venv/bin/python"

import os
import subprocess
import sys

run = [VENV_PYTHON, "./scripts/epu-state-wait", MESSAGING_CONF, CONTROLLER]
runcmd = ' '.join(run)
print runcmd
retcode = subprocess.call(runcmd, shell=True, cwd=APP_DIR, stderr=subprocess.STDOUT)

if retcode:
    print "Problem waiting for EPU controller stable state for '%s'" % CONTROLLER
    sys.exit(retcode)

run = [VENV_PYTHON, "./scripts/epu-state-wait", MESSAGING_CONF, CONTROLLER2]
runcmd = ' '.join(run)
print runcmd
retcode = subprocess.call(runcmd, shell=True, cwd=APP_DIR, stderr=subprocess.STDOUT)

if retcode:
    print "Problem waiting for EPU controller stable state for '%s'" % CONTROLLER2

sys.exit(retcode)
