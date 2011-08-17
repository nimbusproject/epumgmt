import os
import re
import types
import shutil
import tempfile
import datetime
import nose.tools
import ConfigParser
from nose.plugins.attrib import attr

import epumgmt.defaults.svc_adapter
import epumgmt.main.em_args as em_args
from cloudinitd.user_api import CloudInitD

from epumgmt.api.exceptions import *
from epumgmt.api import  RunVM
from epumgmt.defaults import DefaultParameters
from epumgmt.defaults import DefaultRunlogs
from epumgmt.defaults import DefaultRemoteSvcAdapter
from mocks.common import FakeCommon
from mocks.modules import FakeModules
from mocks.event import Event


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

    def test_intake_query_result_from_file(self):

        controller_name = "test-controller"
        de_state = "STABLE_DE"
        de_conf_report = "balala"
        instance_0 = "fashfjsahfjksa"
        instance_0_state = "600-RUNNING"
        iaas_state_time = 12312142
        heartbeat_state = "SOMETHING"
        heartbeat_time = 5


        (json_file, json_filename) = tempfile.mkstemp()
        os.close(json_file)
        test_json = """
        {"%s": {"de_state":"%s", "de_conf_report":"%s",
         "instances": {
           "%s": {"iaas_state":"%s", "iaas_state_time": %s,
                  "heartbeat_state":"%s", "heartbeat_time": %s}}}}
        """ % (controller_name, de_state, de_conf_report
              , instance_0, instance_0_state, iaas_state_time,
              heartbeat_state, heartbeat_time)

        with open(json_filename, "w") as j_file:
            j_file.write(test_json)

        map = self.svc_adapter._intake_query_result_from_file(json_filename)

        # Test that all our values are correct
        assert map.has_key(controller_name)
        controller = map[controller_name]
        assert controller.de_state == de_state
        assert controller.de_conf_report == de_conf_report
        assert len(controller.instances) == 1
        instance = controller.instances[0]
        assert instance.nodeid == instance_0
        assert instance.iaas_state == instance_0_state
        assert instance.iaas_state_time == iaas_state_time
        assert instance.heartbeat_state == heartbeat_state
        assert instance.heartbeat_time == heartbeat_time

    def test_intake_query_result_from_file_new_json(self):
        """Test that new json is parsed correctly

        This test can be used to parse real examples of json produced
        by the system.
        """

        test_dir = os.path.dirname(__file__)

        test_file = os.path.join(test_dir, "data/test_intake_query_result_from_file_new_json.dat")
        map = self.svc_adapter._intake_query_result_from_file(test_file)
        assert map

    def test_intake_query_result(self):

        provisioner = RunVM()
        provisioner.runlogdir = tempfile.mkdtemp()

        local_filename = "log.json"
        remote_filename = "something"
        local_abs_filepath = os.path.join(provisioner.runlogdir, local_filename)

        controller_name = "test-controller"
        de_state = "STABLE_DE"
        de_conf_report = "balala"
        instance_0 = "fashfjsahfjksa"
        instance_0_state = "600-RUNNING"
        iaas_state_time = 12312142
        heartbeat_state = "SOMETHING"
        heartbeat_time = 5


        test_json = """
        {"%s": {"de_state":"%s", "de_conf_report":"%s",
         "instances": {
           "%s": {"iaas_state":"%s", "iaas_state_time": %s,
                  "heartbeat_state":"%s", "heartbeat_time": %s}}}}
        """ % (controller_name, de_state, de_conf_report,
              instance_0, instance_0_state, iaas_state_time,
              heartbeat_state, heartbeat_time)

        with open(local_abs_filepath, "w") as j_file:
            j_file.write(test_json)
        
        self.svc_adapter.initialize(self.m, self.run_name, self.cloudinitd)

        # Test detection of non-existant files
        try:
            fake_file = "not_a_file"
            self.svc_adapter._intake_query_result(provisioner, fake_file, remote_filename)
            raised_unexpected_error = False
        except UnexpectedError:
            raised_unexpected_error = True

        assert raised_unexpected_error

        # Test reading a file actually works
        # all of the other values should be tested by test_intake_query_result_from_file
        map = self.svc_adapter._intake_query_result(provisioner, local_filename, remote_filename)
        assert map.has_key(controller_name)


    def test_run_one_command(self):

        svc_adapter = DefaultRemoteSvcAdapter(self.p, self.c)

        command_to_succeed = "true"
        succeeded = svc_adapter._run_one_cmd(command_to_succeed)
        assert succeeded


        non_existant_command = "a4f6d2f32r22c3c34c423c2f2g34"
        succeeded = svc_adapter._run_one_cmd(non_existant_command)
        assert not succeeded

        
        command_to_fail = "cat fsdbjkfsdy89fsdy89fsfsdfsdfsd"
        succeeded = svc_adapter._run_one_cmd(command_to_fail)
        assert not succeeded


    @attr("slow")
    def test_run_one_command_timeout(self):
        """
        This tests _run_one_command's timeout feature, so you may want
        to skip it when running these tests frequently.
        """

        command_that_will_timeout = "sleep 10000"
        svc_adapter = DefaultRemoteSvcAdapter(self.p, self.c)
        succeeded = svc_adapter._run_one_cmd(command_that_will_timeout)
        assert not succeeded


    def test_get_pathconfs(self):

        source = "something"
        username = "fordprefect"

        self.svc_adapter.initialize(self.m, self.run_name, self.cloudinitd)
        
        abs_homedir, abs_envfile = self.svc_adapter._get_pathconfs(source, username)
        print abs_homedir, abs_envfile
        assert abs_homedir == "/home/%s/app" % username
        assert abs_envfile == "/home/%s/app-venv/bin/activate" % username

    def test_get_provisioner(self):

        self.svc_adapter.initialize(self.m, self.run_name, self.cloudinitd)
        provisioner = self.svc_adapter._get_provisioner()
        
        assert provisioner.name == "provisioner"


    def test_latest_iaas_status(self):

        self.svc_adapter.initialize(self.m, self.run_name, self.cloudinitd)

        vm = RunVM()
        vm.instanceid = "i-dfs3f32"

        try:
            status = self.svc_adapter.latest_iaas_status(None)
            raised_programming_error = False
        except ProgrammingError:
            raised_programming_error = True
        assert raised_programming_error

        
        # Test response when there's no status in VM object
        status = self.svc_adapter.latest_iaas_status(vm)
        assert not status


        vm.events = []
        vm_iaas_state_0 = "RUNNING"
        vm_timestamp_0 = datetime.datetime(2000, 10, 3)
        vm_iaas_state_1 = "SOMETHINGELSE"
        vm_timestamp_1 = datetime.datetime(2000, 10, 5)
        vm.events.append(Event(name="iaas_state", state=vm_iaas_state_0, timestamp=vm_timestamp_0))
        vm.events.append(Event(name="iaas_state", state=vm_iaas_state_1, timestamp=vm_timestamp_1))

        status = self.svc_adapter.latest_iaas_status(vm)
    
        assert status == vm_iaas_state_1


def make_fake_run_one_cmd(target, real_run_one_cmd):
    def fake_run_one_cmd(target, cmd):
        cmd = "echo %s" % cmd
        return real_run_one_cmd(cmd)

    return fake_run_one_cmd
