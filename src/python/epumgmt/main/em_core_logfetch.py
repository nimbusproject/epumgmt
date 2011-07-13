from epumgmt.api.exceptions import *
from epumgmt.main.em_core_load import get_cloudinit
import epumgmt.defaults.epustates as epustates
from em_core_status import _find_state_from_events as find_state_from_events

from threading import Thread

THREADS_PER_BATCH = 20

class FetchThread(Thread):
    
    def __init__ (self, worker, c, m, scpcmd):
        Thread.__init__(self)
        self.worker = worker
        self.iid = worker.instanceid # convenience
        self.scpcmd = scpcmd
        self.c = c
        self.m = m
        self.error = None
        
    def run(self):
        try:
            self.m.runlogs.fetch_logs(self.scpcmd)
            self.c.log.info("Fetched logs from '%s'" % self.iid)
        except Exception,e:
            self.c.log.error("error retrieving logs from '%s'" % self.iid)
            self.error = e

def fetch_all(p, c, m, run_name, cloudinitd):
    """Fetch log files from any VM instance that is part of the run
    that we know about.
    """
    if c.trace:
        c.log.debug("fetch_all()")
    
    run_vms = _get_runvms_required(c, m, run_name, cloudinitd)

    threads = []
    for vm in run_vms:
        scpcmd = m.runlogs.get_scp_command_str(c, vm, cloudinitd)
        if not scpcmd:
            continue
        threads.append(FetchThread(vm, c, m, scpcmd))
    
    txt = "%d service" % len(run_vms)
    if len(run_vms) != 1:
        txt += "s"
    c.log.info("Beginning to logfetch %s" % txt)
    
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
    
    if error_count > 1:
        c.log.info("All fetched with %d errors (%s)" % (error_count, txt))
    elif error_count == 1:
        c.log.info("All fetched with 1 error (%s)" % txt)
    else:
        c.log.info("All fetched (%s)" % txt)

def fetch_by_vm_id(p, c, m, run_name, instanceid):
    """Fetch log files from the VM instance in this run with a particular ID
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    c.log.debug("fetch_by_vm_id()")
    
    run_vms = _get_runvms_required(c, m, run_name, None)
        
    vm = None
    for avm in run_vms:
        if avm.instanceid == instanceid:
            vm = avm
            break
    if not vm:
        raise IncompatibleEnvironment("Cannot find an active VM associated with run '%s' with the instance id '%s'" % (run_name, instanceid))
        
    _fetch_one_vm(p, c, m, run_name, vm)

def fetch_by_service_name(p, c, m, run_name, servicename, cloudinitd=None):
    """Fetch log files from the VM instance(s) in this run that were started
    with the role of this service name.
    
    For example, when the "sleeper" EPU infrastructure is launched, you
    can fetch from nodes that were launched for this only.  If you want to
    retrieve the logs from any worker VM of an HA service that epumgmt
    has found out about, you must use the suffix of the HA service name.
    See: epumgmt.api.RunVM.WORKER_SUFFIX
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    if c.trace:
        c.log.debug("fetch_by_service_name()")
    
    run_vms = _get_runvms_required(c, m, run_name, None)
    
    vms = []
    for avm in run_vms:
        if avm.service_type == servicename:
            vms.append(avm)
            
    if not len(vms):
        raise IncompatibleEnvironment("Cannot find any active VMs associated with run '%s' with the service type/name '%s'" % (run_name, servicename))
    
    for vm in vms:
        _fetch_one_vm(p, c, m, run_name, vm, cloudinitd=cloudinitd)
        
# -----------------------------------------------------------------

def _get_runvms_required(c, m, run_name, cloudinitd):
    run_vms = m.persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)

    if cloudinitd:
        m.remote_svc_adapter.initialize(m, run_name, cloudinitd)
        if m.remote_svc_adapter.is_channel_open():
            c.log.info("Getting status from the EPU controllers, to filter out non-running workers from log fetch")
        else:
            c.log.warn("Cannot get worker status: there is no channel open to the EPU controllers")

    run_vms = filter(lambda x: find_state_from_events(x) != epustates.TERMINATED, run_vms)

    return run_vms

def _fetch_one_vm(p, c, m, run_name, vm, cloudinitd=None):
    c.log.info("fetching logs from '%s' instance '%s' (run '%s')" % (vm.service_type, vm.instanceid, run_name))
    if not cloudinitd:
        cloudinitd = get_cloudinit(p, c, m, run_name)
    scpcmd = m.runlogs.get_scp_command_str(c, vm, cloudinitd)
    m.runlogs.fetch_logs(scpcmd)
