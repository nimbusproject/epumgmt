import unittest
import nose.tools
import sys
import os
import uuid

from epumgmt.api import *

import run_rabbit

class TestSimpleOps(unittest.TestCase):

    def setUp(self):
        self.runname = str(uuid.uuid1()).replace("-", "")
        conf = os.path.join(os.environ['EPUMGMT_HOME'], "etc/epumgmt/main.conf")
        self.epu_opts = EPUMgmtOpts(conf_file=conf)
        self.my_vars_file = os.environ['EPU_TEST_VARS']
        self.epu_opts.jsonvars = self.my_vars_file
        self.epu_action = EPUMgmtAction(self.epu_opts)
        self.epu_action.set_logfile(os.path.join(os.environ['EPUMGMT_HOME'], "tests/tests.logs"))


    def tearDown(self):
        self.epu_action.kill(self.runname)

    def test_main_sequence(self):
        self.epu_opts.haservice = "provisioner"
        self.epu_action.create(self.runname)
