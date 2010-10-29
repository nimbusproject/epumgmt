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
import traceback

from epumgmt.api import *
from epumgmt.main import *
from cloudminer import CloudMiner
from epumgmt.main.em_core_persistence import Persistence

import time

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
    s_retry_count = 5
    worker_count = 2  # need to get this from conf file

    print "RUNNAME IS %s" % (runname)

    service_name = os.environ['EPU_SERVICE']
    rc = 0
    error_msg = "SUCCESS"
    try:
        print "starting provisioner"
        epu_opts.haservice = "provisioner"
        epu_opts.action = ACTIONS.CREATE
        epumgmt_run(epu_opts)

        print "starting %s" % (service_name)
        epu_opts.haservice = service_name
        epu_opts.action = ACTIONS.CREATE
        epumgmt_run(epu_opts)

        epu_opts.haservice = None
        pre_kill_len = 0
        retry_count = s_retry_count
        while pre_kill_len != 2 + worker_count: 
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

        print "make sure hostnames have been achieved"
        done = False
        while not done:
            done = True
            epu_opts.action = ACTIONS.LOGFETCH
            epumgmt_run(epu_opts)

            print "finding workers hostnames"
            epu_opts.action = ACTIONS.FIND_WORKERS_ONCE
            epumgmt_run(epu_opts)

            cyvm_a = cm.get_iaas_by_runname(runname)
            for c in cyvm_a:
                if c.hostname == None or c.hostname.strip() == "":
                    done = False
            cm.commit()

        epu_opts.action = ACTIONS.STATUS
        epumgmt_run(epu_opts)

        orig_iaas_ids = [c.iaasid for c in cyvm_a]

        print "KILLING A WORKER!"
        epu_opts.killnum = 1
        epu_opts.action = ACTIONS.FETCH_KILL
        epumgmt_run(epu_opts)

        cyvm_a = None
        post_kill_len = 0
        retry_count = s_retry_count
        while post_kill_len <= pre_kill_len:
            print "fetch logs"
            epu_opts.action = ACTIONS.LOGFETCH
            epumgmt_run(epu_opts)

            print "finding workers"
            epu_opts.action = ACTIONS.FIND_WORKERS_ONCE
            epumgmt_run(epu_opts)

            cyvm_a = cm.get_iaas_by_runname(runname)
            post_kill_len = len(cyvm_a)
            retry_count = retry_count - 1
            if retry_count < 0:
                raise Exception("No new workers found after %d tries" % (s_retry_count))
            cm.commit()
            time.sleep(10)

        epu_opts.action = ACTIONS.STATUS
        epumgmt_run(epu_opts)

        new_iaas_ids = [c.iaasid for c in cyvm_a]

        orig_iaas_ids.sort()
        new_iaas_ids.sort()
        if orig_iaas_ids == new_iaas_ids:
            raise Exception("The iaas ids did not change: %s -> %s" % (str(orig_iaas_ids), str(new_iaas_ids)))

    except Exception, ex:
        traceback.print_tb(sys.exc_info()[2])
        print "========= ERROR ===================="
        print ex
        print "============================="
        error_msg = str(ex)
        rc = 1

    finally:
        epu_opts.action = ACTIONS.KILLRUN
        epumgmt_run(epu_opts)

    print error_msg

    return rc

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

