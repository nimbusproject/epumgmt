from epumgmt.api.exceptions import *

def update_events(p, c, m, run_name):
    """Parse events from log files and fill the VM instances.
    p,c,m are seen everywhere: parameters, common, modules
    """
    m.event_gather.populate_run_vms(m, run_name)

def _get_runvms_required(persistence, run_name):
    run_vms = persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
    return run_vms
