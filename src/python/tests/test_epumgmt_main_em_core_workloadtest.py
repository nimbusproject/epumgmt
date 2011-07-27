import re
import os
import types
import signal
import tempfile
import datetime
import ConfigParser

from nose.plugins.attrib import attr

import epumgmt.main.em_core_workloadtest

from mocks.amqp import FakeAMQPServer
from mocks.common import FakeCommon
from mocks.modules import FakeModules
from mocks.modules import make_fake_execute_cmd
from cloudinitd.user_api import CloudInitD
from epumgmt.defaults import DefaultParameters
from epumgmt.defaults import DefaultCommon
from epumgmt.main.em_core_workloadtest import EPUController, Torque, AMQP
from epumgmt.api.exceptions import InvalidConfig, ProgrammingError

class TestEPUController:

    def setup(self):

        self.run_name = "testrun"
        runlogdir = tempfile.mkdtemp()
        os.mkdir(os.path.join(runlogdir, self.run_name))

        config = ConfigParser.RawConfigParser()
        config.add_section("events")
        config.set("events", "runlogdir", runlogdir)

        self.m = FakeModules()
        self.p = DefaultParameters(config, None)
        self.c = FakeCommon(self.p)


    def test_init(self):

        # Test no config provided
        badp = DefaultParameters(None, None)
        try:
            EPUController(badp, None, None, None)
            raised_invalid_config = False
        except InvalidConfig:
            raised_invalid_config = True

        assert raised_invalid_config

        # Test with working config
        epucontroller = EPUController(self.p, self.c, self.m, self.run_name)
        assert epucontroller
        assert epucontroller.controllerlog.endswith("controllerkill.log")
        assert epucontroller.controllerlog.startswith(epucontroller.controllerlogdir)


    def test_log_event(self):

        epucontroller = EPUController(self.p, self.c, self.m, self.run_name)

        log_message = "This is an exciting message. Important, as well."

        epucontroller._log_event(log_message)

        with open(epucontroller.controllerlog) as log:
            assert log_message in log.read()

    def test_get_log_time(self):

        # Test only that we get a time that is parsable. Assume we're getting correct time
        epucontroller = EPUController(self.p, self.c, self.m, self.run_name)

        time = epucontroller._get_log_time()
        parsed = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S.%f")
        assert parsed

    def test_start(self):

        epucontroller = EPUController(self.p, self.c, self.m, self.run_name)
        starts = 0

        epucontroller.start()
        starts += 1
        with open(epucontroller.controllerlog) as log:
            log_read = log.read()
            assert log_read.count("EPU_CONTROLLER_START") == starts

        epucontroller.start(num=2)
        starts += 2
        with open(epucontroller.controllerlog) as log:
            log_read = log.read()
            assert log_read.count("EPU_CONTROLLER_START") == starts
        
    def test_terminate(self):

        epucontroller = EPUController(self.p, self.c, self.m, self.run_name)
        terminates = 0

        epucontroller.terminate()
        terminates += 1
        with open(epucontroller.controllerlog) as log:
            log_read = log.read()
            assert log_read.count("EPU_CONTROLLER_TERMINATE") == terminates

        epucontroller.terminate(num=2)
        terminates += 2
        with open(epucontroller.controllerlog) as log:
            log_read = log.read()
            print log_read.count("EPU_CONTROLLER_TERMINATE")
            assert log_read.count("EPU_CONTROLLER_TERMINATE") == terminates


class TestTorque:

    def setup(self):

        self.run_name = "testrun"
        runlogdir = tempfile.mkdtemp()
        os.mkdir(os.path.join(runlogdir, self.run_name))

        config = ConfigParser.RawConfigParser()
        config.add_section("events")
        config.set("events", "runlogdir", runlogdir)

        self.m = FakeModules()
        self.p = DefaultParameters(config, None)
        self.c = FakeCommon(self.p)

        self.test_dir = os.path.dirname(__file__)
        self.test_db_dir = tempfile.mkdtemp()
        self.test_cd_config = os.path.join(self.test_dir, "configs/main.conf")
        self.cloudinitd = CloudInitD(self.test_db_dir, self.test_cd_config, self.run_name)

        
    def test_execute_cmd(self):

        torque = Torque(self.p, self.c, self.m, self.run_name, self.cloudinitd)
        self.c.trace = True

        command_to_succeed = "true"
        success = torque._execute_cmd(command_to_succeed)
        assert success

        non_existant_command = "neo23n3io2j4023um409m23u904m23"
        success = torque._execute_cmd(non_existant_command)
        assert not success

        command_to_fail = "cat neo23n3io2j4023um409m23u904m23"
        success = torque._execute_cmd(command_to_fail)
        assert not success

    @attr("slow")
    def test_execute_cmd_timeout(self):
        """This test is pretty slow (it waits for a timeout). so you
           may want to skip it.
        """

        torque = Torque(self.p, self.c, self.m, self.run_name, self.cloudinitd)

        slow_command = "sleep 60"
        success = torque._execute_cmd(slow_command)
        assert not success


    def test_copy_file(self):

        torque = Torque(self.p, self.c, self.m, self.run_name, self.cloudinitd)

        remote_hostname = "example.com"
        torque.svc._svc._s.hostname = remote_hostname

        # monkey patch execute command to prepend an echo
        new_execute_command = make_fake_execute_cmd(torque, torque._execute_cmd)
        torque._execute_cmd = types.MethodType(new_execute_command, torque)

        test_file = "/path/to/some/file"
        test_file_base = os.path.basename("/path/to/some/file")

        torque._copy_file(test_file)

        run_commands = [message for (level, message)
                        in self.c.log.transcript
                        if level == "DEBUG"
                           and "command = 'echo " in message]

        print run_commands

        # confirm file is copied
        assert [scp_command for scp_command
                in run_commands
                if re.match(".*scp.*%s.*%s:/tmp" % (test_file, remote_hostname), scp_command)
               ]

        # confirm file's permissions are fixed
        assert [ssh_command for ssh_command
                in run_commands
                if re.match(".*ssh.*%s.*chmod ugo\+r.*/tmp/.*%s" % (remote_hostname, test_file_base),
                            ssh_command)
               ]


    def test_qsub_job(self):
        
        torque = Torque(self.p, self.c, self.m, self.run_name, self.cloudinitd)
        remote_hostname = "example.com"
        torque.svc._svc._s.hostname = remote_hostname
        # monkey patch execute command to prepend an echo
        new_execute_command = make_fake_execute_cmd(torque, torque._execute_cmd)
        torque._execute_cmd = types.MethodType(new_execute_command, torque)

        job_name = "test.sh"
        
        torque._qsub_job(job_name)
        run_commands = [message for (level, message)
                        in self.c.log.transcript
                        if level == "DEBUG"
                           and "command = 'echo " in message]

        print run_commands

        # confirm qsub sent
        assert [ssh_command for ssh_command
                in run_commands
                if re.match(".*ssh.*%s.*qsub /tmp/%s.*" % (remote_hostname, job_name),
                            ssh_command)
               ]

    def test_submit(self):

        torque = Torque(self.p, self.c, self.m, self.run_name, self.cloudinitd)
        remote_hostname = "example.com"
        torque.svc._svc._s.hostname = remote_hostname
        # monkey patch execute command to prepend an echo
        new_execute_command = make_fake_execute_cmd(torque, torque._execute_cmd)
        torque._execute_cmd = types.MethodType(new_execute_command, torque)

        job = epumgmt.main.em_core_workloadtest.WorkItem(0, 1, 1, 1)

        torque.submit(job)

        print self.c.log.transcript
        run_commands = [message for (level, message)
                        in self.c.log.transcript
                        if level == "DEBUG"
                           and "command = 'echo " in message]

        print run_commands

        # confirm qsub sent
        assert [ssh_command for ssh_command
                in run_commands
                if re.match(".*ssh.*%s.*qsub.*" % (remote_hostname),
                            ssh_command)
               ]

class TestAMQP:

    def setup(self):


        self.host = "localhost"
        self.port = "8000"

        self.run_name = "testrun"
        runlogdir = tempfile.mkdtemp()
        os.mkdir(os.path.join(runlogdir, self.run_name))

        config = ConfigParser.RawConfigParser()
        config.add_section("events")
        config.set("events", "runlogdir", runlogdir)

        self.m = FakeModules()
        self.p = DefaultParameters(config, None)
        self.c = FakeCommon(self.p)

        self.amqp = AMQP(self.p, self.c, self.m, self.run_name, self.host, self.port)

        self.child_pid = os.fork()
        if self.child_pid == 0:
            # This is the child
            server = FakeAMQPServer()
            sys.exit(0)

    def teardown(self):
        # Kill child process just in case...
        os.kill(self.child_pid, signal.SIGKILL)

    def test_submit_ok(self):

        job = epumgmt.main.em_core_workloadtest.WorkItem(0, 1, 1, 1)
        self.amqp.submit(job)
        print self.c.log.transcript
        message = self.c.log.transcript[0][1]
        url = (self.host, self.port, self.run_name, job.batchid, job.count, job.sleepsec)
        assert message == "submit: http://%s:%s/%s-jobs/%s/%s/%s" % url

    def test_submit_not_ok(self):
        """Ensure that we get an error when server isn't running
        """
        os.kill(self.child_pid, signal.SIGKILL)

        job = epumgmt.main.em_core_workloadtest.WorkItem(0, 1, 1, 1)
        self.amqp.submit(job)
        print self.c.log.transcript
        message_type = self.c.log.transcript[-1][0]
        assert message_type == "ERROR"



