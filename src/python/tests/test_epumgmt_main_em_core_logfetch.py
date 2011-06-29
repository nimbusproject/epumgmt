import re
import os
import types
import shutil
import tempfile
import ConfigParser

import epumgmt.api
import epumgmt.main.em_core_logfetch
from epumgmt.defaults.parameters import DefaultParameters
from cloudinitd.user_api import CloudInitD
from epumgmt.defaults.runlogs import DefaultRunlogs
import epumgmt.main.em_args as em_args

from mocks.common import FakeCommon
from mocks.modules import FakeModules
from mocks.modules import build_fake_scp_command_str

class TestLogfetch:

    def setup(self):
        """
        Build a fake test environment, with the sleepers cloudinit.d plan.

        We can grab all logged messages from c.log.transcript.
        """

        self.test_run_name = "TESTRUN"

        self.config = ConfigParser.RawConfigParser()
        self.config.add_section("events")
        self.runlogdir = tempfile.mkdtemp()
        self.config.set("events", "runlogdir", self.runlogdir)
        self.vmlogdir = tempfile.mkdtemp()
        self.config.set("events", "vmlogdir", self.vmlogdir)
        self.optdict = {}
        self.optdict[em_args.NAME.name] = self.test_run_name

        self.params = DefaultParameters(self.config, None)
        self.params.optdict = self.optdict
        self.common = FakeCommon()
        self.modules = FakeModules()

        # Note that we monkey-patch the get_scp_command_str function
        # to prepend "echo" to it. That way we can still allow the 
        # command to be run, but we can still see how it actually gets
        # constructed
        runlogs = DefaultRunlogs(self.params, self.common)
        runlogs.validate()
        self.modules.runlogs = runlogs
        new_get_scp = build_fake_scp_command_str(runlogs, runlogs.get_scp_command_str)
        self.modules.runlogs.get_scp_command_str = types.MethodType(new_get_scp, self.modules.runlogs)

        self.test_dir = os.path.dirname(__file__)
        self.test_db_dir = tempfile.mkdtemp()
        self.test_cd_config = os.path.join(self.test_dir, "configs/main.conf")
        self.cloudinitd = CloudInitD(self.test_db_dir, self.test_cd_config, self.test_run_name)
        print dir(self.cloudinitd.get_service("provisioner")._svc._s)
        print self.cloudinitd.get_service("provisioner")._svc._s.hostname

    def teardown(self):
        shutil.rmtree(self.test_db_dir)

    def test_fetch_one_vm(self):
        from epumgmt.main.em_core_logfetch import _fetch_one_vm

        test_vm = epumgmt.api.RunVM()

        _fetch_one_vm(self.params, self.common, self.modules,
                      self.test_run_name, test_vm, cloudinitd=self.cloudinitd)

    def test_fetch_by_service_name(self):
        """
        This test constructs a RunVM instance, and then asks
        logfetch to grab its logs. We confirm that the correct
        scp call was made indirectly by examining the transcript
        of the log files.

        We also neuter the scp call by prefixing it with echo, since
        we're not trying to scp from a real host.
        """

        from epumgmt.main.em_core_logfetch import fetch_by_service_name

        test_service_name = "provisioner"

        test_provisioner = epumgmt.api.RunVM()
        test_provisioner.service_type = test_service_name
        test_provisioner_hostname = "test.hostname.example.com"
        test_provisioner.hostname = test_provisioner_hostname
        test_provisioner_vmlogdir = "/some/fake/logdir"
        test_provisioner.vmlogdir = test_provisioner_vmlogdir
        test_provisioner_runlogdir = "/some/fake/local/runlogdir"
        test_provisioner.runlogdir = test_provisioner_runlogdir
        test_provisioner_instanceid = "i-TEST"
        test_provisioner.instanceid = test_provisioner_instanceid

        test_run_vms = []
        test_run_vms.append(test_provisioner)
        self.modules.persistence.store_run_vms(self.test_run_name, test_run_vms)

        # Be tricky and patch in our hostname
        self.cloudinitd.get_service("provisioner")._svc._s.hostname = test_provisioner_hostname

        fetch_by_service_name(self.params, self.common, self.modules,
                              self.test_run_name, test_service_name, self.cloudinitd)

        run_commands = [message for (level, message)
                        in self.common.log.transcript 
                        if level == "DEBUG"
                           and "command =" in message]

        # confirm that scp command gets called for our service 
        expected_scp_pattern = ".*@%s:%s %s" % (test_provisioner_hostname,
                                                test_provisioner_vmlogdir,
                                                test_provisioner_runlogdir)
        # only expect one command to be run
        assert len(run_commands) == 1
        assert re.search(expected_scp_pattern, run_commands[0])
