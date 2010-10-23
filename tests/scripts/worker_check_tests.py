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
import httplib

import epumgmt
import epumgmt.api
from epumgmt.api import *
from epumgmt.main import *
from cloudminer import CloudMiner
from epumgmt.main.em_core_persistence import Persistence

def main(argv=sys.argv[1:]):

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

        epu_opts.haservice = "sleeper"
        epu_opts.action = ACTIONS.CREATE
        epumgmt_run(epu_opts)

        epu_opts.haservice = None

        s_retry_count = 10
        pre_kill_len = 0
        retry_count = s_retry_count
        while pre_kill_len != 4:
            print "finding workers"
            epu_opts.action = ACTIONS.FIND_WORKERS_ONCE
            epumgmt_run(epu_opts)

            cyvm_a = cm.get_iaas_by_runname(runname)
            cm.commit()
            pre_kill_len = len(cyvm_a)
            retry_count = retry_count - 1
            if retry_count < 0:
                raise Exception("No new workers found after %d tries" % (s_retry_count))
            time.sleep(10)

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

