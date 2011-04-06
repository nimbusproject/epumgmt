from epumgmt.api.exceptions import *
from epumgmt.api import RunVM
from epumgmt.main import em_args
from epumgmt.main.em_core_logfetch import FetchThread
import cloudyvents.cyvents as cyvents
from epumgmt.main import em_core_status

THREADS_PER_BATCH = 20

def fetch_kill(p, c, m, run_name, cloudinitd, controller_name=None):
    """Get logs and then kill a worker.
    If controller_name is not supplied to this function, it is expected to be in the cmdline args
    """

    if not controller_name:
        controller_name = p.get_arg_or_none(em_args.CONTROLLER)
    if not controller_name:
        raise InvalidInput("fetch-kill requires a controller")

    m.remote_svc_adapter.initialize(m, run_name, cloudinitd)
    # Get the latest information, especially for IaaS status and controller correlation
    em_core_status.find_latest_status(p, c, m, run_name, cloudinitd, findworkersfirst=False)

    killnum = _get_killnum(p)
    all_workers = _get_workers(p, c, m, run_name)

    # filter out any workers that are from other controllers
    controller_workers = m.remote_svc_adapter.filter_by_controller(all_workers, controller_name)

    # now filter out any workers that are terminating/terminated
    alive_workers = m.remote_svc_adapter.filter_by_running(controller_workers)

    alivenum = len(alive_workers)
    if alivenum:
        c.log.info("Found %d workers we can kill" % alivenum)
    else:
        c.log.error("Found no workers we can kill")
        return
    
    # either choose all remaining or pick N from the group
    if killnum >= alivenum:
        tokill_list = alive_workers
        c.log.warn("You want to kill %d workers but the program only knows about %d running: proceeding to kill all possible" % (killnum, alivenum))
    else:
        tokill_list = alive_workers[:killnum]

    fetch_kill_byID(p, c, m, run_name, cloudinitd, tokill_list, get_workerstatus=False)

def fetch_kill_byID(p, c, m, run_name, cloudinitd, tokill_list, get_workerstatus=True):
    """Get logs and then kills a list of workers

    tokill_list -- RunVM instances
    """

    m.remote_svc_adapter.initialize(m, run_name, cloudinitd)

    if get_workerstatus:
        # Get the latest information, especially for IaaS status and controller correlation
        em_core_status.find_latest_status(p, c, m, run_name, cloudinitd, findworkersfirst=False)

    threads = []
    for one_kill in tokill_list:
        scpcmd = m.runlogs.get_scp_command_str(c, one_kill, cloudinitd)
        threads.append(FetchThread(one_kill, c, m, scpcmd))

    txt = "%d worker" % len(tokill_list)
    if len(tokill_list) != 1:
        txt += "s"
    c.log.info("Beginning to fetch and kill %s" % txt)

    done = False
    idx = 0
    while not done:
        current_batch = threads[idx:idx+THREADS_PER_BATCH]
        idx += THREADS_PER_BATCH
        if idx > len(threads):
            done = True
            
        for thr in current_batch:
            thr.start()
           
        for thr in current_batch:
            thr.join()
        
    error_count = 0
    for thr in threads:
        if thr.error:
            error_count += 1
            msg = "** Issue with %s:\n" % thr.worker.instanceid
            msg += str(thr.error)
            c.log.error("\n\n%s\n" % msg)

    # terminate even if there was an error log fetching

    # provisioner is given the nodeid, not instanceid
    nodeid_list = []
    for one_kill in tokill_list:
        nodeid_list.append(one_kill.nodeid)

    m.remote_svc_adapter.kill_workers(nodeid_list)

    for one_kill in tokill_list:
        extradict = {"iaas_id":one_kill.instanceid, "controller": one_kill.parent}
        cyvents.event("epumgmt", "fetch_killed", c.log, extra=extradict)

    if error_count:
        c.log.info("All fetched and killed with %d fetch errors" % error_count)
    else:
        c.log.info("All fetched and killed")

    return error_count
        
def _get_killnum(p):
    killnum = p.get_arg_or_none(em_args.KILLNUM)
    if killnum is None:
        raise InvalidInput("This action requires %s integer > 0" % em_args.KILLNUM.long_syntax)
        
    try:
        killnum = int(killnum)
        if killnum < 1:
            raise Exception()
    except:
        raise InvalidInput("%s needs to be an integer > 0" % em_args.KILLNUM.long_syntax)
    
    return killnum

def _get_workers(p, c, m, run_name):
    run_vms = _get_runvms_required(m.persistence, run_name)
    vms = []
    for avm in run_vms:
        # todo: 'unknown' is hardcoded.  The 'parent' field provides controller info.
        if avm.service_type == "unknown" + RunVM.WORKER_SUFFIX:
            vms.append(avm)
    return vms

def _get_runvms_required(persistence, run_name):
    run_vms = persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
    return run_vms
