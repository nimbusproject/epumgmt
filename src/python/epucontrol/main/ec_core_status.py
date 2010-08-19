from epucontrol.api.exceptions import *

def status(p, c, m, run_name):
    """Print out status/hostname info that epucontrol knows about each
    instance in the run."""
    
    run_vms = m.persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
        
    widest = _widest_state(run_vms)
    state = m.iaas.state_map(run_vms)
    
    default_typetxt = "(unknown)"
    if len(default_typetxt) > widest:
        widest = len(default_typetxt)
    
    default_typetxt = _pad_txt(default_typetxt, widest)
    
    warnings = []
    actives = []
    
    default_hostname = "(unknown)"
    for vm in run_vms:
        typetxt = default_typetxt
        hostname = default_hostname
        if vm.service_type:
            typetxt = _pad_txt(vm.service_type, widest)
        if vm.hostname:
            hostname = vm.hostname
        vm_info = (typetxt, vm.instanceid, hostname)
        if not state.has_key(vm.instanceid):
            warnings.append("IaaS is not aware of %s | %s | %s" % vm_info)
        else:
            vm_info = (state[vm.instanceid],) + vm_info
            actives.append(vm_info)
    
    if actives:
        actives.sort()
        out = "\n\n"
        for vm_info in actives:
            out += "%s | %s | %s | %s\n" % vm_info
        c.log.info(out + "\n")
        
    if warnings:
        out = "\n\n"
        for warning in warnings:
            out += "%s\n" % warning
        c.log.warn(out + "\n")

def _widest_state(run_vms):
    widest = 0
    for vm in run_vms:
        if vm.service_type:
            if len(vm.service_type) > widest:
                widest = len(vm.service_type)
    return widest

def _pad_txt(txt, widest):
    if len(txt) >= widest:
        return txt
    difference = widest - len(txt)
    while difference:
        txt += " "
        difference -= 1
    return txt
        
        