import os
import re
import types
import shutil
import tempfile
import nose.tools
import ConfigParser

import epumgmt.defaults.svc_adapter
import epumgmt.main.em_args as em_args
from cloudinitd.user_api import CloudInitD

from epumgmt.api.exceptions import *
from epumgmt.api import  RunVM
from epumgmt.defaults import DefaultParameters
from epumgmt.defaults import DefaultRunlogs
from mocks.common import FakeCommon
from mocks.modules import FakeModules


@nose.tools.raises(ProgrammingError)
def test_initialize_no_modules():
    adapter = epumgmt.defaults.svc_adapter.DefaultRemoteSvcAdapter(None, None)
    adapter.initialize(None, None, None)

@nose.tools.raises(ProgrammingError)
def test_initialize_no_run_name():
    adapter = epumgmt.defaults.svc_adapter.DefaultRemoteSvcAdapter(None, None)
    adapter.initialize("fake", None, None)

@nose.tools.raises(ProgrammingError)
def test_initialize_no_cloudinitd():
    adapter = epumgmt.defaults.svc_adapter.DefaultRemoteSvcAdapter(None, None)
    adapter.initialize("fake", "fake", None)

@nose.tools.raises(ProgrammingError)
def test_check_init():
    adapter = epumgmt.defaults.svc_adapter.DefaultRemoteSvcAdapter(None, None)
    adapter._check_init()

class TestDefaultRemoteSvcAdapter:

    def setup(self):
        from epumgmt.defaults.svc_adapter import DefaultRemoteSvcAdapter

        self.run_name = "TESTRUN"

        self.config = ConfigParser.RawConfigParser()
        self.config.add_section("events")
        self.runlogdir = tempfile.mkdtemp()
        self.config.set("events", "runlogdir", self.runlogdir)
        self.vmlogdir = tempfile.mkdtemp()
        self.config.set("events", "vmlogdir", self.vmlogdir)
        self.config.add_section("svcadapter")
        self.config.set("svcadapter", "controller_prefix", "controller")
        self.config.set("svcadapter", "homedir", "app")
        self.config.set("svcadapter", "envfile", "app-venv/bin/activate")
        self.optdict = {}
        self.optdict[em_args.NAME.name] = self.run_name

        self.p = DefaultParameters(self.config, None)
        self.p.optdict = self.optdict



        self.m = FakeModules()
        self.c = FakeCommon()
        self.svc_adapter = DefaultRemoteSvcAdapter(self.p, self.c)

        runlogs = DefaultRunlogs(self.p, self.c)
        self.m.runlogs = runlogs
        runlogs.validate()

        new_run_one_cmd = make_fake_run_one_cmd(self.svc_adapter,
                                                self.svc_adapter._run_one_cmd)
        self.svc_adapter._run_one_cmd = types.MethodType(new_run_one_cmd,
                                                         self.svc_adapter)

        self.test_dir = os.path.dirname(__file__)
        self.test_db_dir = tempfile.mkdtemp()
        self.test_cd_config = os.path.join(self.test_dir, "configs/main.conf")
        self.cloudinitd = CloudInitD(self.test_db_dir, self.test_cd_config, self.run_name)

    def teardown(self):
        
        shutil.rmtree(self.test_db_dir)
        shutil.rmtree(self.runlogdir)
        shutil.rmtree(self.vmlogdir)

    def test_worker_state(self):

        # Check when nothing's passed to worker_state
        try:
            self.svc_adapter.worker_state(None, None)
            raised_incompatible_env = False
        except IncompatibleEnvironment:
            raised_incompatible_env = True
        assert raised_incompatible_env

        provisioner = RunVM()

        # Check when not initialized yet
        try:
            self.svc_adapter.worker_state(None, provisioner)
            raised_programming_error = False
        except ProgrammingError:
            raised_programming_error = True
        assert raised_programming_error


        self.svc_adapter.initialize(self.m, self.run_name, self.cloudinitd)
        # Check when no controllers provided
        try:
            self.svc_adapter.worker_state(None, provisioner)
            raised_invalid_input = False
        except InvalidInput:
            raised_invalid_input = True
        assert raised_invalid_input


        controllers = ["one", "two"]
        try:
            self.svc_adapter.worker_state(controllers, provisioner)
            raised_incompatible_env = False
        except IncompatibleEnvironment:
            raised_incompatible_env = True
        assert raised_incompatible_env


        provisioner.hostname = "some.fake.hostname"
        provisioner.service_type = "provisioner"
        provisioner.runlogdir = self.runlogdir
        self.svc_adapter.provisioner._svc._s.hostname = provisioner.hostname
        try:
            self.svc_adapter.worker_state(controllers, provisioner)
        except UnexpectedError as e:
            print e.msg
            assert "Expecting to find the state query result here" in e.msg

        ssh_commands = [message for (level, message)
                        in self.c.log.transcript 
                        if level == "DEBUG"
                           and "command = 'echo ssh" in message]
        ssh_command = ssh_commands[0]

        # Make sure epu-state called for provisioner
        assert re.match(".*ssh.*%s.*epu-state" % provisioner.hostname, ssh_command)
        # Make sure we query both controllers
        assert re.match(".*epu-state.*%s" % controllers[0], ssh_command)
        assert re.match(".*epu-state.*%s" % controllers[1], ssh_command)


    def test_reconcile_relative_conf(self):

        absolute_dir = "/path/to/conf"
        relative_dir = "path/to/conf"
        user = "thetestuser"

        self.svc_adapter.initialize(self.m, self.run_name, self.cloudinitd)
        got_path = self.svc_adapter._reconcile_relative_conf(absolute_dir, "", "")

        assert got_path == absolute_dir

        try:
            got_path = self.svc_adapter._reconcile_relative_conf(relative_dir, "", "")
            raised_incompatible_env = False
        except IncompatibleEnvironment:
            raised_incompatible_env = True

        assert raised_incompatible_env

        got_path = self.svc_adapter._reconcile_relative_conf(relative_dir, user, "")
        assert got_path == "/home/%s/%s" % (user, relative_dir)


def make_fake_run_one_cmd(target, real_run_one_cmd):
    def fake_run_one_cmd(target, cmd):
        cmd = "echo %s" % cmd
        return real_run_one_cmd(cmd)

    return fake_run_one_cmd
