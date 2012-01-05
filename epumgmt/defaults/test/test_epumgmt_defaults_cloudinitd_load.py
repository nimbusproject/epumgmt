import os
import types
import tempfile
import ConfigParser

from cloudinitd.user_api import CloudInitD

import epumgmt
import epumgmt.defaults.cloudinitd_load
import epumgmt.main.em_args as em_args
from epumgmt.api.exceptions import ProgrammingError, IncompatibleEnvironment
from epumgmt.defaults.runlogs import DefaultRunlogs
from epumgmt.defaults.parameters import DefaultParameters

from epumgmt.mocks.common import FakeCommon
from epumgmt.mocks.modules import FakeModules
from epumgmt.mocks.modules import make_fake_scp_command_str
from epumgmt.mocks.remote_svc_adapter import FakeRemoteSvcAdapter

class TestCloudinitdLoad:
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

        self.test_dir = os.path.dirname(epumgmt.__file__)
        self.test_db_dir = tempfile.mkdtemp()
        self.test_cd_config = os.path.join(self.test_dir, "mocks", "configs", "main.conf")
        self.cloudinitd = CloudInitD(self.test_db_dir, self.test_cd_config, self.test_run_name)

    def test_get_cloudinitd_service(self):
        from epumgmt.defaults.cloudinitd_load import get_cloudinitd_service

        try:
            get_cloudinitd_service(None, None)
        except ProgrammingError:
            no_cloudinitd_programming_error = True

        assert no_cloudinitd_programming_error

        try:
            get_cloudinitd_service(self.cloudinitd, None)
        except ProgrammingError:
            no_service_name_programming_error = True

        assert no_service_name_programming_error

        nonexistant_svc = "notreal"

        try:
            service = get_cloudinitd_service(self.cloudinitd, nonexistant_svc)
        except IncompatibleEnvironment:
            no_service_incompatible_env = True

        assert no_service_incompatible_env

