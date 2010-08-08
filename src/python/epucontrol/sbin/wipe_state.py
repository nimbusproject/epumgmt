#!/usr/bin/env python

import os
import sys
import time
from epucontrol.sbin import sbin_common

def get_logfiledir(p):
    logfiledir = p.get_conf_or_none("logging", "logfiledir")
    if not logfiledir:
        sys.stderr.write("There is no logfiledir configuration")
        return None
    return sbin_common.apply_vardir_maybe(p, logfiledir)

def get_persistencedir(p):
    persistencedir = p.get_conf_or_none("persistence", "persistencedir")
    if not persistencedir:
        sys.stderr.write("There is no persistencedir configuration")
        return None
    return sbin_common.apply_vardir_maybe(p, persistencedir)

def get_runlogdir(p):
    runlogdir = p.get_conf_or_none("events", "runlogdir")
    if not runlogdir:
        sys.stderr.write("There is no runlogdir configuration")
        return None
    return sbin_common.apply_vardir_maybe(p, runlogdir)
    
if len(sys.argv) != 2:
    sys.stderr.write("This program requires 1 argument, the absolute path to the main.conf file")
    sys.exit(1)

p = sbin_common.get_parameters(sys.argv[1])

logfiledir = get_logfiledir(p)
if not logfiledir:
    sys.exit(1)

persistencedir = get_persistencedir(p)
if not persistencedir:
    sys.exit(1)

runlogdir = get_runlogdir(p)
if not runlogdir:
    sys.exit(1)
    
runlogdirs = []
for root, dirs, files in os.walk(runlogdir, topdown=False):
    for adir in dirs:
        path = os.path.join(root, adir)
        runlogdirs.append(path)

# find the newest file in the directory:

sys.stderr.write("Log file dir:    %s\n" % logfiledir)
sys.stderr.write("Persistence dir: %s\n" % persistencedir)
sys.stderr.write("Runlog dir:      %s\n" % runlogdir)
for adir in runlogdirs:
    sys.stderr.write("    subdir:      %s\n" % adir)
    
try:
    yn = sbin_common.get_user_input("\nDelete all these files? Are you sure? y/n")
    yn = yn.lower()
except KeyboardInterrupt:
    sys.stderr.flush()
    sys.stderr.write("\n\nExiting, nothing was deleted.\n")
    sys.exit(2)

if yn != "y" and yn != "yes":
    sys.stderr.flush()
    sys.stderr.write("\n\nExiting, nothing was deleted.\n")
    sys.exit(2)

print ""

for root, dirs, files in os.walk(logfiledir):
    for name in files:
        path = os.path.join(root, name)
        if name.startswith("."):
            sys.stderr.write("Skip: %s\n" % path)
        elif os.path.isfile(path):
            sys.stderr.write("Deleting: %s\n" % path)
            os.remove(path)
    break # only look in the top directory

for root, dirs, files in os.walk(persistencedir):
    for name in files:
        path = os.path.join(root, name)
        if name.startswith("."):
            sys.stderr.write("Skip: %s\n" % path)
        elif name.endswith("lock"):
            sys.stderr.write("Skip: %s\n" % path)
        elif os.path.isfile(path):
            sys.stderr.write("Deleting: %s\n" % path)
            os.remove(path)
    break # only look in the top directory

for adir in runlogdirs:
    for root, dirs, files in os.walk(adir):
        for name in files:
            path = os.path.join(adir, name)
            if os.path.isfile(path):
                sys.stderr.write("Deleting: %s\n" % path)
                os.remove(path)
    sys.stderr.write("Deleting directory: %s\n" % adir)
    os.rmdir(adir)
