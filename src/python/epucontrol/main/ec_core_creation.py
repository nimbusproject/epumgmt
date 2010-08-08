from epucontrol.defaults import RunVM 

def create(p, c, iaas, persistence, runlogs, services, run_name):
    """Create a VM instance that is part of the EPU infrastructure."""
    
    (instanceid, hostname) = iaas.launch()
    
    vm = RunVM()
    vm.instanceid = instanceid
    vm.hostname = hostname
    
    runlogs.new_vm(vm)
    persistence.new_vm(run_name, vm)
    c.log.debug("persisted info about '%s', host '%s'" % (vm.instanceid, vm.hostname))
    
    iaas.contextualize_base_image(services, hostname)
    c.log.info("Contextualized '%s' for run '%s'" % (services.servicename, run_name))
    
    # Confirm sanity-check event happened
    
    
    
    # Convenience print at end
    sshcmd = iaas.ssh_cmd(hostname)
    c.log.info("\nSSH suggestion:\n%s" % ' '.join(sshcmd))
    

