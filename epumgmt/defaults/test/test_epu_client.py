import os
import tempfile

from cloudinitd.user_api import CloudInitD

import epumgmt

from epumgmt.defaults.epu_client import MockEPUClient, DashiEPUClient
from epumgmt.mocks.parameters import FakeParameters

class TestEPUClient(object):

    def setup(self):
        self.p = FakeParameters()
        self.client = MockEPUClient()
        self.client.initialize()

    def test_killrun(self):
        self.client.killrun()

        assert not self.client.alive

class TestDashiEPUClient(TestEPUClient):

    def setup(self):
        from nose.plugins.skip import Skip, SkipTest

        self.test_run_name = "TESTRUN"
        self.test_dir = os.path.dirname(epumgmt.__file__)
        self.test_db_dir = tempfile.mkdtemp()
        self.test_cd_config = os.path.join(self.test_dir, "mocks", "configs", "main.conf")
        self.cloudinitd = CloudInitD(self.test_db_dir, self.test_cd_config,
                self.test_run_name, boot=True)
        self.provisioner_cid = self.cloudinitd.get_service("provisioner")
        provisioner_attrs = self.provisioner_cid._svc._attr_bag
        provisioner_attrs['rabbitmq_username'] = "guest"
        provisioner_attrs['rabbitmq_password'] = "guest"
        provisioner_attrs['broker_ip_address'] = "localhost"

        self.p = FakeParameters()

        self.client = DashiEPUClient(self.p, None)
        self.client.initialize(None, None, self.cloudinitd)

        try:
            self.client.query()
        except:
            raise SkipTest # Only run this test when an instance of EPU is running
