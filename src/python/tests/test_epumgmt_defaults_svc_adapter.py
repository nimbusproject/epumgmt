import nose.tools
import os
import tempfile
import ConfigParser

import epumgmt.defaults.svc_adapter
import epumgmt.main.em_args as em_args
from cloudinitd.user_api import CloudInitD

from epumgmt.api.exceptions import *
from epumgmt.api import  RunVM
from epumgmt.defaults.parameters import DefaultParameters
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

        self.test_dir = os.path.dirname(__file__)
        self.test_db_dir = tempfile.mkdtemp()
        self.test_cd_config = os.path.join(self.test_dir, "configs/main.conf")
        self.cloudinitd = CloudInitD(self.test_db_dir, self.test_cd_config, self.run_name)


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


