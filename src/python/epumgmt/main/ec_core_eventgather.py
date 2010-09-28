from epucontrol.api.exceptions import *
import epucontrol.main.ec_args as ec_args

def update_events(p, c, m, run_name):
    """Parse events from log files and fill the VM instances.
    If the servicename is an argument, only do it for the VMs related
    to that service.
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    
    servicename = p.get_arg_or_none(ec_args.HASERVICE)
    if not servicename:
        m.event_gather.populate_run_vms(m, run_name)
    else:
        run_vms = _get_runvms_required(m.persistence, run_name)
        vms = []
        for avm in run_vms:
            if avm.service_type == servicename:
                m.event_gather.populate_one_vm(m, run_name, avm.instanceid)

def _get_runvms_required(persistence, run_name):
    run_vms = persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
    return run_vms
