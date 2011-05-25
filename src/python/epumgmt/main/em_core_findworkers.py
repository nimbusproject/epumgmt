import em_core_eventgather
import em_core_logfetch
from epumgmt.api import RunVM
from epumgmt.api.exceptions import *
from epumgmt.defaults import is_piggybacked

PROVISIONER="provisioner"

def find_once(p, c, m, run_name):
    
    em_core_logfetch.fetch_by_service_name(p, c, m, run_name, PROVISIONER)
    em_core_eventgather.update_events(p, c, m, run_name)

    # order is important, first "new_node"
    launched_vms = vms_launched(m, run_name, "new_node")
    for vm in launched_vms:
        if m.persistence.new_vm(run_name, vm):
            c.log.info("Found new worker: %s : %s"
                        % (vm.instanceid, vm.hostname))

    # then "node_started"
    launched_vms = vms_launched(m, run_name, "node_started")
    for vm in launched_vms:
        m.persistence.new_vm(run_name, vm)

    allsvcs = m.persistence.get_run_vms_or_none(run_name)
    vm_num = 0
    for svc in allsvcs:
        if not is_piggybacked(svc):
            vm_num += 1

    c.log.debug("Know of %d services on %d VMs in run '%s'" % (len(allsvcs), vm_num, run_name))

def vms_launched(m, run_name, eventname):
    provisioner = _get_provisioner(m, run_name)
    vms = []
    for event in provisioner.events:
        if event.name == eventname:
            vm = RunVM()
            if eventname == "new_node":
                vm.instanceid = event.extra['iaas_id']
                vm.nodeid = event.extra['node_id']
            elif eventname == "node_started":
                vm.instanceid = event.extra['iaas_id']
                vm.nodeid = event.extra['node_id']
            else:
                raise IncompatibleEnvironment("eventname is illegal")
            vm.hostname = event.extra['public_ip']
            # todo: 'unknown' is hardcoded in fetchkill, too
            vm.service_type = "unknown" + vm.WORKER_SUFFIX
            m.runlogs.new_vm(vm)
            vms.append(vm)
    return vms

def _get_provisioner(m, run_name):
    allvms = m.persistence.get_run_vms_or_none(run_name)
    provisioner = None
    for vm in allvms:
        if vm.service_type == PROVISIONER:
            provisioner = vm
    if not provisioner:
        raise IncompatibleEnvironment("Cannot find a record of the provisioner for run '%s'" % run_name)
    return provisioner
