import cloudyvents.cyvents as cyvents
import os

from epumgmt.api.exceptions import *

class DefaultEventGather:
        
    def __init__(self, params, common):
        self.p = params
        self.c = common
    
    def validate(self):
        pass
    
    def populate_run_vms(self, m, run_name):
        self._populate_run_vms(m.persistence, run_name)
        
    def populate_one_vm(self, m, run_name, instanceid):
        self._populate_one_vm(m.persistence, run_name, instanceid)
        
    def _populate_run_vms(self, persistence, run_name):
        run_vms = persistence.get_run_vms_or_none(run_name)
        if not run_vms or len(run_vms) == 0:
            raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)
        for vm in run_vms:
            self._fill_one(vm)
        persistence.store_run_vms(run_name, run_vms)
        
    def _populate_one_vm(self, persistence, run_name, instanceid):
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
        if not vm.runlogdir:
            self.c.log.warn("Svc/VM has no runlogdir, so cannot parse events: %s" % vm.runlogdir)
            return
        all_events = self._all_events_in_dir(vm.runlogdir)
        for event in all_events:
            skip = False
            if (event.name == 'job_sent') or \
               (event.name == 'job_begin') or \
               (event.name == 'job_end'):
                skip = True
            if not skip:
                new = True
                for curevent in vm.events:
                    if event.key == curevent.key:
                        seen = "seen event before, skipping (%s)" % event.key
                        #self.c.log.debug(seen)
                        new = False
                        break
                if new:
                    event_txt = "New event: %s" % event.key
                    event_txt += "\n    source: %s, " % event.source
                    event_txt += "name: %s, " % event.name
                    event_txt += "timestamp: %s" % event.timestamp
                    event_txt += "\n    extra: %s" % event.extra
                    self.c.log.debug(event_txt)
                    vm.events.append(event)
    
    def _all_events_in_dir(self, logdir):
        self.c.log.debug("Getting events from '%s'" % logdir)
        events = []
        for fullpath in self.dirwalk(logdir):
            events.extend(cyvents.events_from_file(fullpath))
        return events

    def dirwalk(self, adir):
        """walk a directory tree, using a generator,
        http://code.activestate.com/recipes/105873-walk-a-directory-tree-using-a-generator/
        """
        for f in os.listdir(adir):
            fullpath = os.path.join(adir,f)
            if os.path.isdir(fullpath) and not os.path.islink(fullpath):
                for x in self.dirwalk(fullpath):  # recurse into subdir
                    yield x
            else:
                yield fullpath
