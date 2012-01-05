import os
import shutil
import tempfile
import ConfigParser

from epumgmt.main.em_core_persistence import Persistence
from epumgmt.defaults import DefaultParameters, DefaultCommon
from epumgmt.api.exceptions import InvalidConfig, ProgrammingError
from epumgmt.api import RunVM

from epumgmt.mocks.common import FakeCommon
from cloudyvents.cyvents import CYvent

class TestPersistence:

    def setup(self):
        self.vardir = tempfile.mkdtemp()
        persistencedir = "persistence"
        persistencefile = "epumgmt.db"
        os.mkdir(os.path.join(self.vardir, persistencedir))
        config = ConfigParser.RawConfigParser()
        config.add_section("persistence")
        config.set("persistence", "persistencedb", persistencefile)
        config.set("persistence", "persistencedir", persistencedir)
        config.add_section("ecdirs")
        config.set("ecdirs", "var", self.vardir)

        params = DefaultParameters(config, None)
        common = FakeCommon(params)

        self.persistence = Persistence(params, common)

    def teardown(self):

        shutil.rmtree(self.vardir)


    def test_find_db_conf(self):

        # Test persistencedb not configured
        params = DefaultParameters(None, None)
        persistence = Persistence(params, None)
        try:
            persistence._find_db_conf()
            raised_invalid_config = False
        except InvalidConfig:
            raised_invalid_config = True
        assert raised_invalid_config


        # Test URL is passed through
        sqlite_url = "sqlite:////path/to/epumgmt.db"

        config = ConfigParser.RawConfigParser()
        config.add_section("persistence")
        config.set("persistence", "persistencedb", sqlite_url)

        params = DefaultParameters(config, None)
        common = FakeCommon()
        persistence = Persistence(params, common)

        dbconf = persistence._find_db_conf()
        assert dbconf == sqlite_url


        # Test relative path, but no persistencedir setting
        relative_path = "fake/path/to/epumgmt.db"

        config = ConfigParser.RawConfigParser()
        config.add_section("persistence")
        config.set("persistence", "persistencedb", relative_path)

        params = DefaultParameters(config, None)
        common = FakeCommon()
        persistence = Persistence(params, common)

        try:
            dbconf = persistence._find_db_conf()
            raised_invalid_config = False
        except InvalidConfig:
            raised_invalid_config = True
        assert raised_invalid_config

        
        # Test persistence dir isn't a dir
        _, persistencedir = tempfile.mkstemp() # note path isn't a dir
        config = ConfigParser.RawConfigParser()
        config.add_section("persistence")
        config.set("persistence", "persistencedb", relative_path)
        config.set("persistence", "persistencedir", persistencedir)

        params = DefaultParameters(config, None)
        common = FakeCommon()
        persistence = Persistence(params, common)

        try:
            dbconf = persistence._find_db_conf()
            raised_invalid_config = False
        except InvalidConfig:
            raised_invalid_config = True
        os.remove(persistencedir)
        assert raised_invalid_config

        
        # Test existant persistence db
        vardir = tempfile.mkdtemp()
        persistencedir = "persistence"
        persistencefile = "epumgmt.db"
        os.mkdir(os.path.join(vardir, persistencedir))
        config = ConfigParser.RawConfigParser()
        config.add_section("persistence")
        config.set("persistence", "persistencedb", persistencefile)
        config.set("persistence", "persistencedir", persistencedir)
        config.add_section("ecdirs")
        config.set("ecdirs", "var", vardir)

        params = DefaultParameters(config, None)
        common = FakeCommon(params)
        persistence = Persistence(params, common)


        dbconf = persistence._find_db_conf()

        shutil.rmtree(vardir)
        assert dbconf.startswith("sqlite:/")
        assert dbconf.endswith(os.path.join(persistencedir, persistencefile)) 

    def test_new_vm(self):

        self.persistence.validate()

        run_name = "testrun"

        vm = RunVM()
        vm.instanceid = "i-4h23ui4"
        vm.nodeid = "hjk-hjk-hjk-hjk-hjk"
        vm.hostname = "fake.example.com"
        vm.service_type = "testservice"
        vm.parent = "myparent"
        vm.runlogdir = "/where/my/logs/are"
        vm.vmlogdir = "/where/my/other/logs/are"
        event_name = "testevent"
        vm.events = [CYvent(None, event_name, None, None, None)]

    
        newvm = self.persistence.new_vm(run_name, vm)
        assert newvm
        cdb_iaas = self.persistence.cdb.get_iaas_by_runname(run_name)
        assert len(cdb_iaas) == 1
        saved_iaas = cdb_iaas[0]
        assert saved_iaas.iaasid == vm.instanceid
        assert saved_iaas.nodeid == vm.nodeid
        assert saved_iaas.hostname == vm.hostname
        assert saved_iaas.service_type == vm.service_type
        assert saved_iaas.parent == vm.parent
        assert saved_iaas.runlogdir == vm.runlogdir
        assert saved_iaas.vmlogdir == vm.vmlogdir
        assert saved_iaas.events[0].name == event_name


    def test_store_run_vms(self):

        # Test when persistence not yet initialized
        try:
            self.persistence.store_run_vms(None, None)
            raised_programming_error = False
        except ProgrammingError:
            raised_programming_error = True
        assert raised_programming_error

        
        # Regular test
        self.persistence.validate()

        run_name = "testrun"

        vm = RunVM()
        vm.instanceid = "i-4h23ui4"
        vm.nodeid = "hjk-hjk-hjk-hjk-hjk"
        vm.hostname = "fake.example.com"
        vm.service_type = "testservice"
        vm.parent = "myparent"
        vm.runlogdir = "/where/my/logs/are"
        vm.vmlogdir = "/where/my/other/logs/are"
        event_name = "testevent"
        vm.events = [CYvent(None, event_name, None, None, None)]
        run_vms = [vm]
        
        self.persistence.store_run_vms(run_name, run_vms)

        cdb_iaas = self.persistence.cdb.get_iaas_by_runname(run_name)
        assert len(cdb_iaas) == 1
        saved_iaas = cdb_iaas[0]
        assert saved_iaas.iaasid == vm.instanceid
        assert saved_iaas.nodeid == vm.nodeid
        assert saved_iaas.hostname == vm.hostname
        assert saved_iaas.service_type == vm.service_type
        assert saved_iaas.parent == vm.parent
        assert saved_iaas.runlogdir == vm.runlogdir
        assert saved_iaas.vmlogdir == vm.vmlogdir
        assert saved_iaas.events[0].name == event_name


    def test_find_instanceid_byservice(self):
        
        # Test when persistence not yet initialized
        try:
            self.persistence.find_instanceid_byservice(None, None)
            raised_programming_error = False
        except ProgrammingError:
            raised_programming_error = True
        assert raised_programming_error
        
        self.persistence.validate()


        # Test regular case
        run_name = "testrun"

        vm0 = RunVM()
        vm0.instanceid = "i-4h23ui4"
        vm0.nodeid = "hjk-hjk-hjk-hjk-hjk"
        vm0.hostname = "fake.example.com"
        vm0.service_type = "testservice"
        vm0.parent = "myparent"
        vm0.runlogdir = "/where/my/logs/are"
        vm0.vmlogdir = "/where/my/other/logs/are"
        run_vms = [vm0]

        self.persistence.store_run_vms(run_name, run_vms)

        got_vm = self.persistence.find_instanceid_byservice(run_name, vm0.service_type)
        assert got_vm == vm0.instanceid


        # Test that we get None when we ask for a non-existant service
        got_vm = self.persistence.find_instanceid_byservice(run_name, "nonexistance-service")
        assert not got_vm


        # Test when we have two services with the same name
        vm1 = RunVM()
        vm1.instanceid = "i-x4h23ui4"
        vm1.nodeid = "xhjk-hjk-hjk-hjk-hjk"
        vm1.hostname = "fakex.example.com"
        vm1.service_type = "testservice"
        vm1.parent = "myparent"
        vm1.runlogdir = "/where/my/logs/are"
        vm1.vmlogdir = "/where/my/other/logs/are"

        run_vms.append(vm1)
        self.persistence.store_run_vms(run_name, run_vms)

        try:
            got_vm = self.persistence.find_instanceid_byservice(run_name, vm0.service_type)
            raised_programming_error = False
        except ProgrammingError:
            raised_programming_error = True
        assert raised_programming_error


    def test_check_new_instanceid(self):

        self.persistence.validate()

        run_name = "testrun"

        vm = RunVM()
        vm.instanceid = "i-4h23ui4"
        vm.nodeid = "hjk-hjk-hjk-hjk-hjk"
        vm.hostname = "fake.example.com"
        vm.service_type = "testservice"
        vm.parent = "myparent"
        vm.runlogdir = "/where/my/logs/are"
        vm.vmlogdir = "/where/my/other/logs/are"

        newvm = self.persistence.new_vm(run_name, vm)
        assert newvm

        assert self.persistence.check_new_instanceid(vm.instanceid)
        assert not self.persistence.check_new_instanceid("i-haventseenyet")


    def test_get_run_vms_or_none(self):

        # Test when persistence not yet validated
        try:
            self.persistence.get_run_vms_or_none(None)
            raised_programming_error = False
        except ProgrammingError:
            raised_programming_error = True
        assert raised_programming_error

        run_name = "testrun"
        
        self.persistence.validate()

        # Test empty case
        assert not self.persistence.get_run_vms_or_none(run_name)

        # Test normal case
        vm = RunVM()
        vm.instanceid = "i-4h23ui4"
        vm.nodeid = "hjk-hjk-hjk-hjk-hjk"
        vm.hostname = "fake.example.com"
        vm.service_type = "testservice"
        vm.parent = "myparent"
        vm.runlogdir = "/where/my/logs/are"
        vm.vmlogdir = "/where/my/other/logs/are"
        event_name = "testevent"
        extra_key = "something"
        extra_val = "else"
        vm.events = [CYvent(None, event_name, None, None, {extra_key:extra_val})]

        newvm = self.persistence.new_vm(run_name, vm)

        got_vms = self.persistence.get_run_vms_or_none(run_name)

        assert len(got_vms) == 1
        
        assert got_vms[0].instanceid == vm.instanceid
        assert got_vms[0].events[0].extra[extra_key] == extra_val
