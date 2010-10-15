"""
This first simple test will run through some very basic tests.  If no
exceptions are thrown and the test completes it is considered successful.
Results are checked in more sophisticated tests.
"""
import unittest
import nose.tools
import sys
import os
import uuid

from epumgmt.api import *
from epumgmt.main import *
from cloudminer import CloudMiner


def main(argv=sys.argv[1:]):

    runname = str(uuid.uuid1()).replace("-", "")
    conf = os.path.join(os.environ['EPUMGMT_HOME'], "etc/epumgmt/main.conf")
    epu_opts = EPUMgmtOpts(name=runname, conf_file=conf)
    my_vars_file = os.environ['EPU_TEST_VARS']
    epu_opts.jsonvars = my_vars_file
    #epu_action.set_logfile(os.path.join(os.environ['EPUMGMT_HOME'], "tests/tests.logs"))

    cyvm_a = []
    try:
        dburl = 'sqlite:////home/bresnaha/Dev/Nimbus/OOI/epumgmt.db'
        cm = CloudMiner(dburl)

        epu_opts.haservice = "provisioner"
        epu_opts.action = ACTIONS.CREATE
        epumgmt_run(epu_opts)

        epu_opts.action = ACTIONS.FIND_WORKERS_ONCE
        epumgmt_run(epu_opts)

        epu_opts.action = ACTIONS.LOGFETCH
        epumgmt_run(epu_opts)

        epu_opts.action = ACTIONS.UPDATE_EVENTS
        epumgmt_run(epu_opts)

        epu_opts.action = ACTIONS.STATUS
        epumgmt_run(epu_opts)

        cyvm_a = cm.get_iaas_by_runname(runname)

    finally:
        epu_opts.action = ACTIONS.KILLRUN
        epumgmt_run(epu_opts)

    if len(cyvm_a) != 1:
        raise Exception("too many vms in miner")
    if c.service_type != "provisioner":
        raise Exception("wrong service type")

    print "SUCCESS"
    return 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

