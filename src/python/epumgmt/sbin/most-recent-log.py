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
    
if len(sys.argv) != 2:
    sys.stderr.write("This program requires 1 argument, the absolute path to the main.conf file")
    sys.exit(1)

p = sbin_common.get_parameters(sys.argv[1])

logfiledir = get_logfiledir(p)
if not logfiledir:
    sys.exit(1)

# find the newest file in the directory:

sys.stderr.write("Log file dir:    %s\n" % logfiledir)

sortme = []
for root, dirs, files in os.walk(logfiledir):
    for name in files:
        path = os.path.join(logfiledir, name)
        if os.path.isfile(path):
            astat = os.stat(path)
            modtime = time.localtime(astat[8])
            sortme.append((modtime, path))
    
    break # only look in the top directory
    
if len(sortme) == 0:
    sys.stderr.write("Could not find any files in: %s" % logfiledir)
    sys.exit(1)
    
sortme.sort()
newest_file = sortme[-1][1]
sys.stderr.write("Newest log file: %s\n" % newest_file)
sys.stderr.flush()

f = open(newest_file)
for line in f:
    print line,
f.close()
