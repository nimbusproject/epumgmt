from epucontrol.api.exceptions import *

def fetch_all(p, c, m, run_name):
    """Fetch log files from any VM instance that is part of the run
    that we know about.
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    if c.trace:
        c.log.debug("fetch_all()")
    
    run_vms = _get_runvms_required(m.persistence, run_name)
        
    for vm in run_vms:
        _fetch_one_vm(p, c, m, run_name, vm)

def fetch_by_vm_id(p, c, m, run_name, instanceid):
    """Fetch log files from the VM instance in this run with a particular ID
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    c.log.debug("fetch_by_vm_id()")
    
    run_vms = _get_runvms_required(m.persistence, run_name)
        
    vm = None
    for avm in run_vms:
        if avm.instanceid == instanceid:
            vm = avm
            break
    if not vm:
        raise IncompatibleEnvironment("Cannot find a VM associated with run '%s' with the instance id '%s'" % (run_name, instanceid))
        
    _fetch_one_vm(p, c, m, run_name, vm)

def fetch_by_service_name(p, c, m, run_name, servicename):
    """Fetch log files from the VM instance(s) in this run that were started
    with the role of this service name.
    
    For example, when the "sleeper" EPU infrastructure is launched, you
    can fetch from nodes that were launched for this only.  If you want to
    retrieve the logs from any worker VM of an HA service that epucontrol
    has found out about, you must use the suffix of the HA service name.
    See: epucontrol.defaults.WORKER_SUFFIX
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    if c.trace:
        c.log.debug("fetch_by_service_name()")
    
    run_vms = _get_runvms_required(m.persistence, run_name)
    
    vms = []
    for avm in run_vms:
        if avm.service_type == servicename:
            vms.append(avm)
            
    if len(vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s' with the service type/name '%s'" % (run_name, servicename))
    
    for vm in vms:
        _fetch_one_vm(p, c, m, run_name, vm)
        
# -----------------------------------------------------------------

def _get_runvms_required(persistence, run_name):
    run_vms = persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
    return run_vms

def _fetch_one_vm(p, c, m, run_name, vm):
    c.log.info("fetching logs from '%s' instance '%s' (run '%s')" % (vm.service_type, vm.instanceid, run_name))
    m.runlogs.fetch_logs(vm, m)
