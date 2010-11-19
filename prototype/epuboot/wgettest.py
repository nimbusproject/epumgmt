#!/usr/bin/env python
import uuid
import os
import sys
import urllib
import time
import filecmp

def setup_http(token):
    print "writting html file for serving"
    f = open("/var/www/test.txt", "w")
    f.write(token)
    f.close()


def wait_forready():
    done = False
    while not done:
        try:
            (tmpfile, headers) = urllib.urlretrieve("http://localhost/test.txt")
            done = True
            rc = filecmp.cmp(tmpfile, "/var/www/test.txt")
            return rc
        except Exception, ex:
            print ex
            time.sleep(10)

def main(argv=sys.argv[1:]):
    setup_http(argv[0])
    rc = wait_forready()
    if rc:
        return 0
    else:
        return 16

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

