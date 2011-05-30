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

@nose.tools.raises(ProgrammingError)
def test_get_class_by_keyword_raises():
    cls = epumgmt.main.get_class_by_keyword("whatever")

@nose.tools.raises(InvalidConfig)
def test_get_class_by_keyword_raises():
    cls = epumgmt.main.get_class_by_keyword("whatever", implstr="fakety.fake")

