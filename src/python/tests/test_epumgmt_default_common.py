import os
import shutil
import logging
import tempfile
import ConfigParser

import epumgmt.defaults.common
from epumgmt.defaults import DefaultCommon
from epumgmt.defaults import DefaultParameters
from epumgmt.api.exceptions import InvalidConfig, UnexpectedError

class TestDefaultCommon:

    def setup(self):

        self.logdir = tempfile.mkdtemp()

        self.ac = ConfigParser.ConfigParser()
        self.ac.add_section("ecdirs")
        self.ac.add_section("logging")
        self.ac.set("logging", "stdoutloglevel", "4")
        self.ac.add_section("emimpls")

        self.p = DefaultParameters(self.ac, None)
        self.common = DefaultCommon(self.p)

    def teardown(self):
        shutil.rmtree(self.logdir)

    def test_init(self):
        
        try:
            epumgmt.defaults.common.DefaultCommon(None)
        except InvalidConfig:
            raised_invalidconfig = True

        assert raised_invalidconfig

    def test_resolve_var_dir(self):

        var_file = "logs"

        try:
            self.common.resolve_var_dir(var_file)
        except InvalidConfig:
            invalid_config_raised = True

        assert invalid_config_raised

        
        self.ac.set("ecdirs", "var", "var/epumgmt")
        got_vardir = self.common.resolve_var_dir(var_file)

        vardir = os.path.join(os.path.dirname(__file__), "../../..", "var/epumgmt", var_file)

        assert os.path.samefile(got_vardir, vardir)


    def test_get_class_by_keyword(self):
        from mocks.common import FakeCommon
        
        test_keyword = "TheClass"
        test_class = "mocks.common.FakeCommon"

        try:
            self.common.get_class_by_keyword(test_keyword)
        except UnexpectedError:
            raised_unexpected_error = True

        assert raised_unexpected_error

        self.ac.set("emimpls", test_keyword, test_class)
            
        kls = self.common.get_class_by_keyword(test_keyword)

        assert kls == FakeCommon

def test_close_logfile():

    # This test runs outside the test object to avoid closing
    # the log file before the other tests can use it
    
    logdir = tempfile.mkdtemp()

    ac = ConfigParser.ConfigParser()
    ac.add_section("ecdirs")
    ac.add_section("logging")
    ac.set("logging", "stdoutloglevel", "4")
    ac.add_section("emimpls")

    ac.set("logging", "logfiledir", logdir)
    ac.set("logging", "fileloglevel", "0")

    params = DefaultParameters(ac, None)
    logging_common = DefaultCommon(params)

    assert os.path.isfile(logging_common.logfilepath)
    assert logging_common.logfilehandler

    logging_common.close_logfile()
    assert not logging_common.logfilehandler

    #logging_common.reopen_logfile()
    #assert logging_common.logfilehandler

    shutil.rmtree(logdir)
