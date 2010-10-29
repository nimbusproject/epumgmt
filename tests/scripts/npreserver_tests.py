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
import tempfile

from epumgmt.api import *
from epumgmt.main import *
from cloudminer import CloudMiner
from epumgmt.main.em_core_persistence import Persistence
import simplejson as json
import time

def test_it(worker_count, my_vars_file):

    runname = str(uuid.uuid1()).replace("-", "")
    conf = os.path.join(os.environ['EPUMGMT_HOME'], "etc/epumgmt/main.conf")
    epu_opts = EPUMgmtOpts(name=runname, conf_file=conf)
    epu_opts.jsonvars = my_vars_file
    #epu_action.set_logfile(os.path.join(os.environ['EPUMGMT_HOME'], "tests/tests.logs"))

    cyvm_a = []
    (c, p, ac) = epumgmt.api.get_common(opts=epu_opts)
    persist = Persistence(p, c)
    persist.validate()
    cm = persist.cdb
    s_retry_count = 10

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

            epu_opts.action = ACTIONS.LOGFETCH
            epumgmt_run(epu_opts)

            cyvm_a = cm.get_iaas_by_runname(runname)
            cm.commit()
            pre_kill_len = len(cyvm_a)
            retry_count = retry_count - 1
            if retry_count < 0:
                raise Exception("No new workers found after %d tries %d" % (s_retry_count, worker_count))
            time.sleep(20)

        epu_opts.action = ACTIONS.STATUS
        epumgmt_run(epu_opts)

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

def main(argv=sys.argv[1:]):

    my_vars_file = os.environ['EPU_TEST_VARS']
    worker_counts = [2, 4, 0]
    for wc in worker_counts:
        print "Trying to preserve %d" % (wc)
        fp = open(my_vars_file, "r")
        jvars = json.load(fp)
        fp.close()
        jvars['min_instances'] = str(wc)
        (osf, filename) = tempfile.mkstemp()
        os.close(osf)
        osf = open(filename, "w")
        j = json.dumps(jvars)
        osf.write(j)
        osf.close()
        print filename
        rc = test_it(wc, filename)
        if rc != 0:
            print "failed on count %d" % (wc)
            return rc
    return 0

if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

