#!/usr/bin/env python

import sys
import string
import random
import os
import sys
import sys
import ConfigParser
from ConfigParser import SafeConfigParser
import time
import tempfile
import traceback
import filecmp
import logging
import shlex
from optparse import SUPPRESS_HELP
import boto
from boto.s3.connection import OrdinaryCallingFormat
from boto.s3.connection import VHostCallingFormat
from boto.s3.connection import SubdomainCallingFormat
from boto.s3.connection import S3Connection
from boto.ec2.connection import EC2Connection
import simplejson as json

def run_rabbit(instance_id=None):

    try:
        ami_id = "ami-3ecc2e57"
        user_id = os.environ['AWS_ACCESS_KEY_ID']
        pw = os.environ['AWS_SECRET_ACCESS_KEY']

        print "getting connection"
        ec2conn = EC2Connection(user_id, pw)

        if instance_id == None:
            print "getting image"
            image = ec2conn.get_image(ami_id)
            print "running it"
            res = image.run()
        else:
            ia = ec2conn.get_all_instances(instance_ids=[instance_id,])
            res = ia[0]
        i = res.instances[0]

        while True:
            print i
            print i.id
            print i.state
            i.update()
            if i.state == "running":
                return i
            elif i.state == "terminated":
                raise Exception("rabbit id already terminated")
            else:
                time.sleep(2)
        return i

    except:
        raise

    return 0

def check_rabbit(hostname, port=5672):

    import socket
    import time

    s = socket.socket()

    error_count = 0
    try_again = True
    while try_again:
        try:
            print "trying to connect to rabbit server %s:%d" % (hostname, port)
            s.connect((hostname, port))
            print "successfully connected to rabbit"
            return
        except Exception, ex:
            print ex
            error_count = error_count + 1
            if error_count > 30:
                raise Exception("could not connect to rabbit server")
            time.sleep(10)

def main(argv=sys.argv[1:]):
    filename = "myvars.json"
    if len(argv) > 0:
        filename = argv[0]

    if len(argv) > 1:
        instance_id = argv[1]
    else:
        instance_id = None

    try:
        instance = run_rabbit(instance_id)
    except Exception, ex:
        print "error: " + str(ex)
        return 1

    json_dict = {}
    json_dict["exchange_scope"] ="cei_hello1"
    json_dict["broker_cookie"] ="unknown"
    json_dict["lcaarch_commit_hash"] ="HEAD"
    json_dict["epuworker_image_id"] ="ami-9ac923f3"
    json_dict["broker_ip_address"] = instance.dns_name
    outs = json.dumps(json_dict)

    print outs
    check_rabbit(instance.dns_name)
    print instance.id
    f = open(filename, "w")
    f.write(outs)
    f.write("\n")
    f.close()

    return 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

