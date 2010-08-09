import fcntl
import os
import pickle
import stat
import sys

from epucontrol.api.exceptions import *
import epucontrol.main.ec_args as ec_args

class Persistence:
    def __init__(self, params, common):
        self.p = params
        self.c = common
        self.pdir = None
        self.lockfilepath = None
        
    def validate(self):
        pdir = self.p.get_conf_or_none("persistence", "persistencedir")
        if not pdir:
            raise InvalidConfig("There is no persistence->persistencedir configuration")
            
        if not os.path.isabs(pdir):
            pdir = self.c.resolve_var_dir(pdir)
            
        if not os.path.exists(pdir):
            try:
                os.mkdir(pdir)
                self.c.log.debug("created persistence directory: %s" % pdir)
            except:
                exception_type = sys.exc_type
                try:
                    exceptname = exception_type.__name__ 
                except AttributeError:
                    exceptname = exception_type
                errstr = "problem creating persistence dir '%s': %s: %s" % (pdir, str(exceptname), str(sys.exc_value))
                
                fullerrstr = "persistence directory does not have valid permissions and cannot be made to have valid permissions: '%s'" % pdir
                fullerrstr += errstr
                self.c.log.error(fullerrstr)
                raise IncompatibleEnvironment(fullerrstr)
            
        if os.access(pdir, os.W_OK | os.X_OK | os.R_OK):
            self.c.log.debug("persistence directory is rwx-able: %s" % pdir)
        else:
            try:
                os.chmod(pdir, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)
            except:
                exception_type = sys.exc_type
                try:
                    exceptname = exception_type.__name__ 
                except AttributeError:
                    exceptname = exception_type
                errstr = " - problem changing persistence directory permissions '%s': %s: %s" % (pdir, str(exceptname), str(sys.exc_value))
                
                fullerrstr = "persistence directory does not have valid permissions and cannot be made to have valid permissions: '%s'" % pdir
                fullerrstr += errstr
                raise IncompatibleEnvironment(fullerrstr)
                
            self.c.log.debug("persistence directory was made to be rwx-able: %s" % pdir)
            
        
        lockfilepath = os.path.join(pdir, "persistence.lock")
        if not os.path.exists(lockfilepath):
            open(lockfilepath, 'w').close()
        
        self.lockfilepath = lockfilepath
        self.pdir = pdir
        
    def new_vm(self, run_name, vm):
        """Adds VM to a run_vms list if it exists for "run_name".  If list
        does not exist, it will be created."""
        return self.run_with_flock(self._new_vm, run_name, vm)
    
    def new_vm_maybe(self, run_name, vm):
        """Adds VM to a run_vms list if it exists for "run_name".  If list
        does not exist, it will be created.  If VM instance ID is present,
        it won't be added."""
        return self.run_with_flock(self._new_vm_maybe, run_name, vm)
        
    def _new_vm(self, run_name, vm):
        """Run this under a lock so that the list is not messed up"""
        run_vms = self.get_run_vms_or_none(run_name)
        if not run_vms:
            run_vms = []
        run_vms.append(vm)
        self.store_run_vms(run_name, run_vms)
    
    def _new_vm_maybe(self, run_name, vm):
        """Run this under a lock so that the list is not messed up"""
        run_vms = self.get_run_vms_or_none(run_name)
        if not run_vms:
            run_vms = []
        found = False
        for avm in run_vms:
            if avm.instanceid == vm.instanceid:
                found = True
        if found:
            return False # not new
        else:
            run_vms.append(vm)
            self.store_run_vms(run_name, run_vms)
            return True
        
    def run_with_flock(self, f, *args, **kw):
        """Run function with persistence's filesystem-based lock.
        
        Would be nice to use a decorator but want to find/create lockfile
        during class instantiation, need to figure that out later.
        
        Anyhow, we will likely switch to SQLite at some point.
        """
        
        lockfile = None
        try:
            lockfile = open(self.lockfilepath, "r")
            fcntl.flock(lockfile.fileno(), fcntl.LOCK_EX)
            return f(*args, **kw)
        finally:
            if lockfile:
                lockfile.close()

    def store_run_vms(self, run_name, run_vms):
        if not self.pdir:
            raise ProgrammingError("cannot persist anything without setup/validation")
            
        if not run_vms:
            raise ProgrammingError("no run_vms")
        
        if not run_name:
            raise ProgrammingError("no run_name")
            
        pobject = self._derive_runset_filepath(run_name)
        
        f = None
        try:
            f = open(pobject, 'w')
            pickle.dump(run_vms, f)
        finally:
            if f:
                f.close()
                
    def get_run_vms_or_none(self, run_name):
        """Get list of VMs for a run name or return None.
        
        If you mutate this list, you should lock first (we will switch
        to SQLite at some point)."""
        
        if not self.pdir:
            raise ProgrammingError("cannot persist anything without setup/validation")
        
        pobject = self._derive_runset_filepath(run_name)
        if not os.path.exists(pobject):
            return None
            
        f = None
        try:
            f = open(pobject, 'r')
            x = pickle.load(f)
            return x
        finally:
            if f:
                f.close()

    def _derive_runset_filepath(self, run_name):
        if not run_name:
            raise ProgrammingError("no run_name")
        return os.path.join(self.pdir, run_name + "-run_vms_list")
        