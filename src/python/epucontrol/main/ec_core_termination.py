
def terminate(p, c, persistence, iaas, run_name):
    if c.trace:
        c.log.debug("create()")
    
    # Should eventually be some lock, etc. (or a sqlite DB), so multiple
    # epucontrols can work on the same run simultaneously, but this works
    # for now.
    run_vms = persistence.get_run_vms_or_none(run_name)
    if not run_vms:
        c.log.warn("Nothing to terminate for run '%s'" % run_name)
        return
        
    for vm in run_vms:
        c.log.info("Terminating '%s', Host '%s'" % (vm.instanceid, vm.hostname))
    
    instanceids = [vm.instanceid for vm in run_vms]
    iaas.terminate_ids(instanceids)
