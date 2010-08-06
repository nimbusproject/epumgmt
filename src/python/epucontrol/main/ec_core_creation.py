from epucontrol.defaults import EPUVM 

def create(p, c, persistence, iaas, services, run_name):
    if c.trace:
        c.log.debug("create()")
    (instanceid, hostname) = iaas.launch()
    
    vm = EPUVM()
    vm.instanceid = instanceid
    vm.hostname = hostname
    
    persistence.new_vm(run_name, vm)
    c.log.debug("persisted info about '%s', host '%s'" % (vm.instanceid, vm.hostname))
    
    iaas.contextualize_base_image(services, hostname)
    
    # Confirm sanity-check event happened
    
    
    
    # Convenience print at end
    sshcmd = iaas.ssh_cmd(hostname)
    c.log.info("\nSSH suggestion:\n%s" % ' '.join(sshcmd))
    
    



