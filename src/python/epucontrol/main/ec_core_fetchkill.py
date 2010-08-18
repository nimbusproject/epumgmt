import epucontrol.main.ec_args as ec_args
from epucontrol.api.exceptions import *
from epucontrol.defaults import RunVM
import cei_events

import random
import time
try:
    from threading import Thread
except ImportError:
    from dummy_threading import Thread

THREADS_PER_BATCH = 20

def fetch_kill(p, c, m, run_name):
    killnum = _get_killnum(p)
    tokill = []
    all_workers = _get_workers(p, c, m, run_name)
    
    # filter out any workers that are terminating/terminated
    alive_workers = m.iaas.filter_by_running(all_workers)
    
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
    
    threads = []
    for one_kill in tokill_list:
        threads.append(FetchKillThread(one_kill, c, m))
    
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
    
    if error_count:
        c.log.info("All fetched and killed with %d errors" % error_count)
    else:
        c.log.info("All fetched and killed")
        
class FetchKillThread(Thread):
    
    def __init__ (self, worker, c, m):
        Thread.__init__(self)
        self.worker = worker
        self.iid = worker.instanceid # convenience
        self.c = c
        self.m = m
        self.error = None
        
    def run(self):
        try:
            #self.c.log.debug("fetching logs from '%s'" % self.iid)
            self.m.runlogs.fetch_logs(self.worker, self.m)
            self.c.log.info("Fetched logs from '%s'" % self.iid)
        except Exception,e:
            self.c.log.error("error retrieving logs from '%s'" % self.iid)
            self.error = e
        
        time.sleep(0.1) # release control
        
        # terminate even if there was an error log fetching
        try:
            #self.c.log.debug("terminating '%s'" % self.iid)
            self.m.iaas.terminate_ids(self.iid)
            self.c.log.info("Terminated '%s'" % self.iid)
            extradict = {"iaas_id":self.iid}
            cei_events.event("epucontrol", "fetch_killed", self.c.log, extra=extradict)
        except Exception,e:
            self.c.log.error("error terminating '%s'" % self.iid)
            self.error = e
    
def _get_killnum(p):
    killnum = p.get_arg_or_none(ec_args.KILLNUM)
    if killnum == None:
        raise InvalidInput("This action requires %s integer > 0" % ec_args.KILLNUM.long_syntax)
        
    try:
        killnum = int(killnum)
        if killnum < 1:
            raise Exception()
    except:
        raise InvalidInput("%s needs to be an integer > 0" % ec_args.KILLNUM.long_syntax)
    
    return killnum

def _get_workers(p, c, m, run_name):
    run_vms = _get_runvms_required(m.persistence, run_name)
    vms = []
    for avm in run_vms:
        # todo: 'unknown' is hardcoded right now
        if avm.service_type == "unknown" + RunVM.WORKER_SUFFIX:
            vms.append(avm)
    return vms

def _get_runvms_required(persistence, run_name):
    run_vms = persistence.get_run_vms_or_none(run_name)
    if not run_vms or len(run_vms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
    return run_vms
