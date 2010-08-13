import epucontrol.main.ec_args as ec_args
import ec_core_eventgather
import ec_core_logfetch
from epucontrol.defaults import RunVM
from epucontrol.api.exceptions import *
import time

PROVISIONER="provisioner"

def find(p, c, m, action, run_name, once=False):
    
    while True:
        ec_core_logfetch.fetch_by_service_name(p, c, m, run_name, PROVISIONER)
        ec_core_eventgather.update_events(p, c, m, run_name)
        
        # order is important, first "new_node"
        launched_vms = vms_launched(p, c, m, run_name, "new_node")
        for vm in launched_vms:
            if m.persistence.new_vm_maybe(run_name, vm):
                c.log.info("Found new worker: %s : %s" 
                            % (vm.instanceid, vm.hostname))
                
        # then "node_started"
        launched_vms = vms_launched(p, c, m, run_name, "node_started")
        for vm in launched_vms:
            m.persistence.new_vm_maybe(run_name, vm)
        
        allvms = m.persistence.get_run_vms_or_none(run_name)
        c.log.debug("Know of %d VMs in run '%s'" % (len(allvms), run_name))
        if once:
            break
        time.sleep(15)

def vms_launched(p, c, m, run_name, eventname):
    provisioner = _get_provisioner(p, c, m, run_name)
    vms = []
    for event in provisioner.events:
        if event.name == eventname:
            vm = RunVM()
            if eventname == "new_node":
                vm.instanceid = event.extra['iaas_id']
            elif eventname == "node_started":
                vm.instanceid = event.extra['node_id']
            else:
                raise IncompatibleEnvironment()
            vm.hostname = event.extra['public_ip']
            vm.service_type = "unknown" + vm.WORKER_SUFFIX
            m.runlogs.new_vm(vm)
            vms.append(vm)
    return vms

def _get_provisioner(p, c, m, run_name):
    allvms = m.persistence.get_run_vms_or_none(run_name)
    provisioner = None
    for vm in allvms:
        if vm.service_type == PROVISIONER:
            provisioner = vm
    if not provisioner:
        raise IncompatibleEnvironment("Cannot find a record of the provisioner for run '%s'" % run_name)
    return provisioner