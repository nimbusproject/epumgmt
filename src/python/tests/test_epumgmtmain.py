import nose.tools

import epumgmt.main
from epumgmt.api.exceptions import InvalidConfig, ProgrammingError

def test_get_class():
    cls = epumgmt.main.get_class("datetime.datetime")
    import datetime
    assert datetime.datetime == cls


def test_get_class_by_keyword():
    cls = epumgmt.main.get_class_by_keyword("whatever", implstr="datetime.datetime")
    import datetime
    assert datetime.datetime == cls

    cls = None

    import ConfigParser
    config = ConfigParser.RawConfigParser()
    config.add_section("emimpls")
    config.set("emimpls", "whatever", "datetime.datetime")
    cls = epumgmt.main.get_class_by_keyword("whatever", allconfigs=config)
    assert datetime.datetime == cls


@nose.tools.raises(ProgrammingError)
def test_get_class_by_keyword_raises():
    cls = epumgmt.main.get_class_by_keyword("whatever")


@nose.tools.raises(InvalidConfig)
def test_get_class_by_keyword_raises():
    cls = epumgmt.main.get_class_by_keyword("whatever", implstr="fakety.fake")


@nose.tools.raises(InvalidConfig)
def test_get_all_configs_relative_path():
    # mwahahaha
    epumgmt.main.get_all_configs("../../../etc/passwd")


def test_get_all_configs():
    import ConfigParser
    import tempfile
    import os

    test_section = "def"
    test_key = "quay"
    test_val = "value"

    sub_test_section = "sub"

    sub_config = ConfigParser.RawConfigParser()
    sub_config.add_section(sub_test_section)
    sub_config.set(sub_test_section, test_key, test_val)

    sub_config_file, sub_config_filename = tempfile.mkstemp()
    os.close(sub_config_file)
    sub_config_file = open(sub_config_filename, "wb")
    sub_config.write(sub_config_file)
    sub_config_file.close()

    config = ConfigParser.RawConfigParser()
    config.add_section(test_section)
    config.set(test_section, test_key, test_val)

    config.add_section("otherconfs")
    config.set("otherconfs", sub_test_section, sub_config_filename)

    config_file, config_filename = tempfile.mkstemp()
    os.close(config_file)
    config_file = open(config_filename, "wb")
    config.write(config_file)
    config_file.close()

    cfg = epumgmt.main.get_all_configs(config_filename)
    
    assert cfg.get(test_section, test_key) == test_val
    assert cfg.get("otherconfs", sub_test_section) == sub_config_filename
    assert cfg.get(sub_test_section, test_key) == test_val
