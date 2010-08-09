from epucontrol.defaults import RunVM
from epucontrol.api.exceptions import *

def create(p, c, m, run_name):
    """Create a VM instance that is part of the EPU infrastructure.
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    if c.trace:
        c.log.debug("create()")
        
    (instanceid, hostname) = m.iaas.launch()
    
    vm = RunVM()
    vm.instanceid = instanceid
    vm.hostname = hostname
    vm.service_type = m.services.servicename
    
    m.runlogs.new_vm(vm)
    m.persistence.new_vm(run_name, vm)
    c.log.debug("persisted info about '%s', host '%s'" % (vm.instanceid, vm.hostname))
    
    m.iaas.contextualize_base_image(m.services, hostname)
    
    # TODO: if --sanity flag, confirm sanity-check event happened
    
    
    # Convenience print at end
    
    msg = "\n\nContextualized '%s' : run '%s': id '%s' : %s" % (m.services.servicename, run_name, vm.instanceid, vm.hostname)
    sshcmd = m.iaas.ssh_cmd(hostname)
    msg += "\n\nSSH suggestion:\n%s" % ' '.join(sshcmd)
    c.log.info(msg)

