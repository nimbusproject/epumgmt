import epumgmt.defaults.svc_adapter
from epumgmt.api.exceptions import *

import nose.tools

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


