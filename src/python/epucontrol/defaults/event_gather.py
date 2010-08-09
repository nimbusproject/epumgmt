import cei_events
import os

from epucontrol.api.exceptions import *

class DefaultEventGather:
        
    def __init__(self, params, common):
        self.p = params
        self.c = common
    
    def validate(self):
        pass
    
    def populate_run_vms(self, m, run_name):
        m.persistence.run_with_flock(self._populate_run_vms, m.persistence, run_name)
        
    def populate_one_vm(self, m, run_name, instanceid):
        m.persistence.run_with_flock(self._populate_one_vm, m.persistence, run_name, instanceid)
        
    def _populate_run_vms(self, persistence, run_name):
        """Run under a lock so that the VMs are not altered by something else"""
        run_vms = persistence.get_run_vms_or_none(run_name)
        if not run_vms or len(run_vms) == 0:
            raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
        for vm in run_vms:
            self._fill_one(vm)
        persistence.store_run_vms(run_name, run_vms)
        
    def _populate_one_vm(self, persistence, run_name, instanceid):
        """Run under a lock so that the VMs are not altered by something else"""
        run_vms = persistence.get_run_vms_or_none(run_name)
        if not run_vms or len(run_vms) == 0:
            raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
        vm = None
        for avm in run_vms:
            if avm.instanceid == instanceid:
                vm = avm
                break
        if not vm:
            raise IncompatibleEnvironment("Cannot find a VM associated with run '%s' with the instance id '%s'" % (run_name, instanceid))
        
        self._fill_one(vm)
        persistence.store_run_vms(run_name, run_vms)
        
    def _fill_one(self, vm):
        # Reaching point where DB would be nice...
        
        if not vm.runlogdir:
            self.c.log.warn("VM has no runlogdir, so cannot parse events: %s" % vm.runlogdir)
            return
        all_events = self._all_events_in_dir(vm.runlogdir)
        for event in all_events:
            new = True
            for curevent in vm.events:
                if event.key == curevent.key:
                    seen = "seen event before, skipping (%s)" % event.key
                    #self.c.log.debug(seen)
                    new = False
                    break
            if new:
                self.c.log.debug("New event: %s" % event.key)
                vm.events.append(event)
    
    def _all_events_in_dir(self, logdir):
        events = []
        for root, dirs, files in os.walk(logdir):
            for name in files:
                path = os.path.join(root, name)
                events.extend(cei_events.events_from_file(path))
            break # only look in the top directory
        return events
