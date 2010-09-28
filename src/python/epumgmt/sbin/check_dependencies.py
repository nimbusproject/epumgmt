#!/usr/bin/env python

import sys

ERR = "** PROBLEM: "

problem_count = 0

version = sys.version
print "Python %s" % version.replace("\n", " | ")

curr = sys.version_info
required = (2,5)

if curr[0] < required[0]:
    print >>sys.stderr, "\n%sThe Python version looks too low, 2.5 is required." % ERR
    problem_count += 1
elif curr[1] < required[1]:
    print >>sys.stderr, "\n%sThe Python version looks too low, 2.5 is required." % ERR
    problem_count += 1

if curr == (2,4):
    print >>sys.stderr, "\n%sPython 2.4 detected: this should work but it is untested and unsupported." % ERR

# --------------------------------------------------------------------------

# This will be a package brought in later, right now it is embedded in lib/
try:
    import cyvents
except ImportError:
    print >>sys.stderr, "\n%sCannot locate the cyvents package." % ERR
    problem_count += 1

# --------------------------------------------------------------------------

try:
    import boto
except ImportError:
    print >>sys.stderr, "\n%sCannot locate the boto package." % ERR
    problem_count += 1

# --------------------------------------------------------------------------

try:
    import simplejson
except ImportError:
    print >>sys.stderr, "\n%sCannot locate the simplejson package." % ERR
    problem_count += 1

# --------------------------------------------------------------------------

if problem_count:
    sys.exit(1)
    
print "\nOK, looks like the dependencies are set up."

