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
from epumgmt.api import *
from epumgmt.main import *

from epumgmt.main import get_class_by_keyword, get_all_configs
import simplejson as json

def get_conf_file():
    conf_file=os.path.join(os.environ['EPUMGMT_HOME'], "etc/epumgmt/main.conf")
    return conf_file

def get_allconfigs():
    conf_file = get_conf_file()
    ac = get_all_configs(conf_file)
    return ac

def get_iaas_object(opts=None):

    if opts == None:
        opts = EPUMgmtOpts(name="XXXX", conf_file=get_conf_file())

    ac = get_allconfigs()
    p_cls = get_class_by_keyword("Parameters", allconfigs=ac)
    p = p_cls(ac, opts)
    c_cls = get_class_by_keyword("Common", allconfigs=ac)
    c = c_cls(p)
    iaas_cls = c.get_class_by_keyword("IaaS")
    iaas = iaas_cls(p, c)
    return iaas

def get_running_instances():
    iaasiface = get_iaas_object()
    con = iaasiface._get_connection()

    running_instances = []
    res_a = con.get_all_instances()
    for res in res_a:
        for i in res.instances:
            if i.state == "running" or i.state == "pending":
                running_instances.append(i)
    return running_instances

def kill_em(instances_a, no_kill):

    for i in no_kill:
        instance_id_a.remove(i)
    iaasiface = get_iaas_object()
    con = iaasiface._get_connection()
    instance_id_a = [i.id for i in instances_a]

    print "stoping %s" % (str(instance_id_a))
    con.terminate_instances(instance_id_a)

def main(argv=sys.argv[1:]):
  
    instances_a = get_running_instances() 

    if len(argv) > 0:
        if argv[0] == "kill":
            no_kill = argv[1:]
            if instances_a:
                kill_em(instances_a, no_kill)
            else:
                print "nothing to terminate"
    for i in instances_a:
        print i.id    

    return 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

