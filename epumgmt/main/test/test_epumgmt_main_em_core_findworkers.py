import epumgmt.main.em_core_findworkers
import epumgmt.api

from epumgmt.api.exceptions import IncompatibleEnvironment
from epumgmt.defaults.runlogs import DefaultRunlogs
import epumgmt.main.em_args as em_args
from epumgmt.defaults.parameters import DefaultParameters

from epumgmt.mocks.common import FakeCommon
from epumgmt.mocks.modules import FakeModules
from epumgmt.mocks.event import Event
from epumgmt.mocks.runlogs import FakeRunlogs

def test_get_provisioner():
    from epumgmt.main.em_core_findworkers import _get_provisioner

    m = FakeModules()
    run_name = "TESTRUN"

    m.persistence.store_run_vms(run_name, [])

    try:
        _get_provisioner(m, run_name)
        raised_incompatible_env = False
    except IncompatibleEnvironment:
        raised_incompatible_env = True

    assert raised_incompatible_env


    non_provisioner_vm = epumgmt.api.RunVM()
    non_provisioner_vm.service_type = "something"

    m.persistence.store_run_vms(run_name, [non_provisioner_vm])

    try:
        _get_provisioner(m, run_name)
        raised_incompatible_env = False
    except IncompatibleEnvironment:
        raised_incompatible_env = True

    assert raised_incompatible_env


    test_service_name = "provisioner"
    test_provisioner = epumgmt.api.RunVM()
    test_provisioner.service_type = test_service_name
    test_provisioner_instanceid = "i-TEST"
    test_provisioner.instanceid = test_provisioner_instanceid

    m.persistence.store_run_vms(run_name, [non_provisioner_vm, test_provisioner])

    got_provisioner = _get_provisioner(m, run_name)

    assert got_provisioner == test_provisioner


def test_vms_launched():
    from epumgmt.main.em_core_findworkers import vms_launched

    run_name = "TESTRUN"

    c = FakeCommon()
    m = FakeModules()

    optdict = {}
    optdict[em_args.NAME.name] = run_name

    p = DefaultParameters(None, None)
    p.optdict = optdict

    m.runlogs = FakeRunlogs()

    test_service_name = "provisioner"
    test_provisioner = epumgmt.api.RunVM()
    test_provisioner.service_type = test_service_name
    test_provisioner_instanceid = "i-TEST"
    test_provisioner.instanceid = test_provisioner_instanceid

    m.persistence.store_run_vms(run_name, [test_provisioner])

    got_vms = vms_launched(m, run_name, "new_node")
    assert got_vms == []


    vm_0_id = "i-apple"
    vm_0_nodeid = "applenodeid"
    vm_0_publicip = "8.8.8.8"
    vm_0_new_node_event = Event(name="new_node", iaas_id=vm_0_id,
                       node_id=vm_0_nodeid, public_ip=vm_0_publicip)

    test_provisioner.events.append(vm_0_new_node_event)

    got_vms = vms_launched(m, run_name, "new_node")
    assert got_vms[0].instanceid == vm_0_id


    test_provisioner.events = []
    got_vms = vms_launched(m, run_name, "new_node")
    assert got_vms == []


    vm_0_node_started_event = Event(name="node_started", iaas_id=vm_0_id,
                                   node_id=vm_0_nodeid, public_ip=vm_0_publicip)
    test_provisioner.events.append(vm_0_node_started_event)
    
    got_vms = vms_launched(m, run_name, "node_started")
    assert got_vms[0].instanceid == vm_0_id


    test_provisioner.events = []
    got_vms = vms_launched(m, run_name, "new_node")
    assert got_vms == []


    vm_0_bad_event = Event(name="bad", iaas_id=vm_0_id,
                                   node_id=vm_0_nodeid, public_ip=vm_0_publicip)
    test_provisioner.events.append(vm_0_bad_event)
    
    try:
        got_vms = vms_launched(m, run_name, "bad")
        raised_incompatible_env = False
    except IncompatibleEnvironment:
        raised_incompatible_env = True
    assert raised_incompatible_env
    
