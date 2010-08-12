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
        launched_vms = vms_launched_by_provisioner(p, c, m, run_name)
        
        for vm in launched_vms:
            if m.persistence.new_vm_maybe(run_name, vm):
                c.log.info("Found new worker: %s : %s" 
                            % (vm.instanceid, vm.hostname))
        
        allvms = m.persistence.get_run_vms_or_none(run_name)
        c.log.debug("Know of %d VMs in run '%s'" % (len(allvms), run_name))
        if once:
            break
        time.sleep(15)

def vms_launched_by_provisioner(p, c, m, run_name):
    allvms = m.persistence.get_run_vms_or_none(run_name)
    provisioner = None
    for vm in allvms:
        if vm.service_type == PROVISIONER:
            provisioner = vm
    if not provisioner:
        raise IncompatibleEnvironment("Cannot find a record of the provisioner for run '%s'" % run_name)
    
    vms = []
    for event in provisioner.events:
        if event.name == "new_node":
            vm = RunVM()
            vm.instanceid = event.extra['iaas_id']
            vm.hostname = event.extra['public_ip']
            vm.service_type = "unknown" + vm.WORKER_SUFFIX
            m.runlogs.new_vm(vm)
            vms.append(vm)
        elif event.name == "node_started":
            vm.hostname = event.extra['public_ip']
            m.persistence.new_vm_maybe(run_name, vm)
    return vms
