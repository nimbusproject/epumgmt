import os
import shutil
import tempfile
import ConfigParser
import epumgmt.api

class TestEpumgmtAPI:

    def setup(self):

        class FakeOpts:
            name = None
        self.opts = FakeOpts()
        self.opts.name = "testname"

        self.epu_home = tempfile.mkdtemp()
        conf_dir = os.path.join(self.epu_home, "etc/")
        os.makedirs(conf_dir)
        self.main_conf = os.path.join(conf_dir, "main.conf")
        self.dirs_conf = os.path.join(conf_dir, "dirs.conf")
        self.internal_conf = os.path.join(conf_dir, "internal.conf")

        main_conf_str = "[otherconfs]\ndirs: dirs.conf\ninternal: internal.conf"

        self.var_dir = "/var/"
        dirs_conf_str = "[ecdirs]\nvar: %s" % self.var_dir

        internal_conf_str = "[emimpls]\n"
        internal_conf_str += "Parameters: epumgmt.defaults.DefaultParameters\n"
        internal_conf_str += "Common: epumgmt.mocks.common.FakeCommon\n"

        with open(self.main_conf, "w") as main:
            main.write(main_conf_str)

        with open(self.dirs_conf, "w") as dirs:
            dirs.write(dirs_conf_str)

        with open(self.internal_conf, "w") as internal:
            internal.write(internal_conf_str)

    def teardown(self):
        shutil.rmtree(self.epu_home)

    def test_get_default_config(self):
        from epumgmt.api import get_default_config

        epumgmt_home = "/path/to/epumgmt"
        default_conf_rel = "etc/main.conf"
        default_config = os.path.join(epumgmt_home, default_conf_rel)
        os.environ["EPUMGMT_HOME"] = epumgmt_home

        assert get_default_config() == default_config

    def test_get_default_ac(self):
        from epumgmt.api import get_default_ac
        from epumgmt.api.exceptions import InvalidConfig

        os.environ["EPUMGMT_HOME"] = self.epu_home

        ac = get_default_ac()

        assert ac.has_section("ecdirs")
        assert ac.has_option("ecdirs", "var")
        assert ac.get("ecdirs", "var") == self.var_dir


    def test_get_parameters(self):
        from epumgmt.api import get_parameters
        from epumgmt.defaults.parameters import DefaultParameters


        ac = ConfigParser.ConfigParser()
        ac.add_section("emimpls")
        ac.set("emimpls", "Parameters", "epumgmt.defaults.parameters.DefaultParameters")
        
        # Test whether we can pass in an allconfigs object
        p, ret_ac = get_parameters(self.opts, ac)

        default_params_class = DefaultParameters(None, None).__class__
        assert p.__class__ == default_params_class
        assert p.get_arg_or_none("name") == self.opts.name

        # Test whether we can get allconfigs from env
        os.environ["EPUMGMT_HOME"] = self.epu_home
        p, ret_ac = get_parameters(self.opts)

        assert ret_ac.has_section("emimpls")
        assert p.__class__ == default_params_class
        assert p.get_arg_or_none("name") == self.opts.name


    def test_get_common(self):
        from epumgmt.api import get_common
        from epumgmt.mocks.common import FakeCommon

        try:
            get_common()
        except:
            no_opts_nor_p_exception = True

        assert no_opts_nor_p_exception

        common_class = FakeCommon().__class__

        os.environ["EPUMGMT_HOME"] = self.epu_home
        c, p, ac = get_common(opts=self.opts)
        
        assert c.__class__ == common_class
        assert p.get_arg_or_none("name") == self.opts.name
        assert ac.has_section("emimpls")
