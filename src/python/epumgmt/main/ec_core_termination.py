from epucontrol.api.exceptions import *

def terminate(p, c, m, run_name):
    """Destroy all VM instances that are part of the run.
    
    p,c,m are seen everywhere: parameters, common, modules 
    """

    if c.trace:
        c.log.debug("terminate()")
    
    run_vms = m.persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
        
    for vm in run_vms:
        c.log.info("Terminating '%s', Host '%s'" % (vm.instanceid, vm.hostname))
    
    instanceids = [vm.instanceid for vm in run_vms]
    m.iaas.terminate_ids(instanceids)
