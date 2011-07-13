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
import epumgmt.defaults.epustates as epustates

from mocks.common import FakeCommon
from mocks.modules import FakeModules
from mocks.modules import make_fake_scp_command_str
from mocks.remote_svc_adapter import FakeRemoteSvcAdapter
from mocks.event import Event

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
        remote_svc_adapter = FakeRemoteSvcAdapter()
        self.common = FakeCommon()
        self.modules = FakeModules(remote_svc_adapter=remote_svc_adapter)

        # Note that we monkey-patch the get_scp_command_str function
        # to prepend "echo" to it. That way we can still allow the 
        # command to be run, but we can still see how it actually gets
        # constructed
        runlogs = DefaultRunlogs(self.params, self.common)
        runlogs.validate()
        self.modules.runlogs = runlogs
        new_get_scp = make_fake_scp_command_str(runlogs, runlogs.get_scp_command_str)
        self.modules.runlogs.get_scp_command_str = types.MethodType(new_get_scp, self.modules.runlogs)

        self.test_dir = os.path.dirname(__file__)
        self.test_db_dir = tempfile.mkdtemp()
        self.test_cd_config = os.path.join(self.test_dir, "configs/main.conf")
        self.cloudinitd = CloudInitD(self.test_db_dir, self.test_cd_config, self.test_run_name)

    def teardown(self):
        shutil.rmtree(self.test_db_dir)
        shutil.rmtree(self.vmlogdir)
        shutil.rmtree(self.runlogdir)

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


    def test_fetch_all(self):

        from epumgmt.main.em_core_logfetch import fetch_all

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

        # Be tricky and patch in our hostname
        self.cloudinitd.get_service("provisioner")._svc._s.hostname = test_provisioner_hostname

        # Two workers. Note that they have the same hostname
        # to simulate the issue where we have a terminated worker
        # and the second one was booted with the same hostname as
        # the first
        test_worker_0 = epumgmt.api.RunVM()
        test_worker_0_service_type = "iamaworker"
        test_worker_0.service_type = test_worker_0_service_type
        test_worker_0_hostname = "worker0.example.com"
        test_worker_0.hostname = test_worker_0_hostname
        test_worker_0_instanceid = "i-TESTWORKER0"
        test_worker_0.instanceid = test_worker_0_instanceid
        test_worker_0_vmlogdir = "/some/fake/logdir"
        test_worker_0.vmlogdir = test_worker_0_vmlogdir
        test_worker_0_runlogdir = "/some/fake/%s/runlogdir" % test_worker_0_instanceid
        test_worker_0.runlogdir = test_worker_0_runlogdir
        test_worker_0_iaas_state = epustates.TERMINATED
        test_worker_0_events = [Event(name="iaas_state", timestamp=1000, state=test_worker_0_iaas_state)]
        test_worker_0.events = test_worker_0_events


        test_worker_1 = epumgmt.api.RunVM()
        test_worker_1_service_type = "iamaworker"
        test_worker_1.service_type = test_worker_0_service_type
        test_worker_1.hostname = test_worker_0_hostname
        test_worker_1_instanceid = "i-TESTWORKER1"
        test_worker_1.instanceid = test_worker_1_instanceid
        test_worker_1_vmlogdir = "/some/fake/logdir"
        test_worker_1.vmlogdir = test_worker_1_vmlogdir
        test_worker_1_runlogdir = "/some/fake/%s/runlogdir/" % test_worker_1_instanceid
        test_worker_1.runlogdir = test_worker_1_runlogdir
        test_worker_1_iaas_state = epustates.RUNNING
        test_worker_1_events = [Event(name="iaas_state", timestamp=1000, state=test_worker_1_iaas_state)]
        test_worker_1.events = test_worker_1_events

        test_run_vms = []
        test_run_vms.append(test_provisioner)
        test_run_vms.append(test_worker_0)
        test_run_vms.append(test_worker_1)
        self.modules.persistence.store_run_vms(self.test_run_name, test_run_vms)

        fetch_all(self.params, self.common, self.modules, self.test_run_name, self.cloudinitd)
        run_commands = [message for (level, message)
                        in self.common.log.transcript 
                        if level == "DEBUG"
                           and "command =" in message]

        # We have two VMs we should fetch from
        assert len(run_commands) == 2



        # Confirm that we never scp log files from the TERMINATED VM
        for scp_command in run_commands:
            assert scp_command.find(test_worker_0_instanceid) == -1

