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

import epumgmt
import epumgmt.api
from epumgmt.api import *
from epumgmt.main import *
from cloudminer import CloudMiner
from epumgmt.main.em_core_persistence import Persistence

def main(argv=sys.argv[1:]):

    service_name = os.environ['EPU_SERVICE']

    runname = str(uuid.uuid1()).replace("-", "")
    conf = os.path.join(os.environ['EPUMGMT_HOME'], "etc/epumgmt/main.conf")
    epu_opts = EPUMgmtOpts(name=runname, conf_file=conf)
    my_vars_file = os.environ['EPU_TEST_VARS']
    epu_opts.jsonvars = my_vars_file
    #epu_action.set_logfile(os.path.join(os.environ['EPUMGMT_HOME'], "tests/tests.logs"))

    cyvm_a = []
    (c, p, ac) = epumgmt.api.get_common(opts=epu_opts)
    persist = Persistence(p, c)
    persist.validate()
    cm = persist.cdb

    try:
        epu_opts.haservice = "provisioner"
        epu_opts.action = ACTIONS.CREATE
        epumgmt_run(epu_opts)

        epu_opts.haservice = service_name
        epu_opts.action = ACTIONS.CREATE
        epumgmt_run(epu_opts)

        cyvm_a = cm.get_iaas_by_runname(runname)

        if len(cyvm_a) != 2:
            raise Exception("the wrong number of VMs found by miner")

        found = 0
        for c in cyvm_a:
            if c.service_type == "provisioner":
                found = found + 1
            elif c.service_type == service_name:
                found = found + 1
            else:
                raise Exception("unknown service type found")
        if found != 2:
            raise Exception("did not find %s and/or provisioner" % (service_name))

    except Exception, ex:
        print ex
        return 1

    finally:
        epu_opts.action = ACTIONS.KILLRUN
        epumgmt_run(epu_opts)


    print "SUCCESS"
    return 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

