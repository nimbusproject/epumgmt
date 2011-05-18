import os
import urlparse
from epumgmt.api import RunVM
from epumgmt.api.exceptions import *
from cloudminer import CloudMiner
from cloudyvents.cyvents import CYvent

class Persistence:
    def __init__(self, params, common):
        self.p = params
        self.c = common
        self.lockfilepath = None
        
    def _find_db_conf(self):
        dbconf = self.p.get_conf_or_none("persistence", "persistencedb")
        if not dbconf:
            raise InvalidConfig("There is no persistence->persistencedb configuration")
        url = urlparse.urlparse(dbconf)
        
        # If it's some kind of URL, return verbatim
        if url.scheme:
            self.c.log.info("Database configuration (verbatim): %s" % dbconf)
            return dbconf
        
        # If it's an absolute path, assuming SQLite.
        # Relative paths are taken from the persistencedir setting.
        
        if not os.path.isabs(dbconf):
            pdir = self.p.get_conf_or_none("persistence", "persistencedir")
            if not pdir:
                raise InvalidConfig("There is no persistence->persistencedir configuration")
                
            if not os.path.isabs(pdir):
                pdir = self.c.resolve_var_dir(pdir)
                
            if not os.path.isdir(pdir):
                raise InvalidConfig("Not a directory: %s" % pdir)
        
            dbconf = os.path.join(pdir, dbconf)
        
        sqlitedbconf = "sqlite:///" + dbconf
        self.c.log.info("Database configuration (deduced): %s" % sqlitedbconf)
        
        if not os.path.exists(dbconf):
            raise InvalidConfig("File does not exist: %s" % dbconf)
            
        return sqlitedbconf
        
            
    def validate(self):
        self.cdb = CloudMiner(self._find_db_conf())
        
    def new_vm(self, run_name, vm):
        """Adds VM to a run_vms list if it exists for "run_name".  If list
        does not exist, it will be created.
        Return True if the VM has not been seen before.
        """
        # vm.events = CYvents
        # vm.instanceid = iaasid
        # runname
        newone = self.cdb.add_cloudyvent_vm(run_name, vm.instanceid, vm.nodeid, vm.hostname, vm.service_type, vm.parent, vm.runlogdir, vm.vmlogdir)
        for e in vm.events:
            self.cdb.add_cloudyvent(run_name, vm.instanceid, vm.nodeid, vm.hostname, vm.service_type, vm.parent, vm.runlogdir, vm.vmlogdir, e)
        self.cdb.commit()
        if newone:
            self.c.log.debug("New VM persisted: '%s'" % vm.instanceid)
        return newone
        
    def store_run_vms(self, run_name, run_vms):
        if not self.cdb:
            raise ProgrammingError("cannot persist anything without setup/validation")
        for vm in run_vms:
            # This will updates some fields if needed, it's not actually "add" but "add only if new"
            self.cdb.add_cloudyvent_vm(run_name, vm.instanceid, vm.nodeid, vm.hostname, vm.service_type, vm.parent, vm.runlogdir, vm.vmlogdir)
            for e in vm.events:
                self.cdb.add_cloudyvent(run_name, vm.instanceid, vm.nodeid, vm.hostname, vm.service_type, vm.parent, vm.runlogdir, vm.vmlogdir, e)
        self.cdb.commit()

    def find_instanceid_byservice(self, run_name, servicename):
        """Expects only zero or 1 result -- you cannot use the "piggybacking service" trick with a non-uniqe name
        """
        if not self.cdb:
            raise ProgrammingError("cannot persist anything without setup/validation")
        cyvm_a = self.cdb.get_vms_by_type(run_name, servicename)
        if len(cyvm_a) > 1:
            raise ProgrammingError("cannot handle non-unique service names here")
        if len(cyvm_a):
            return cyvm_a[0].iaasid
        return None

    def check_new_instanceid(self, instanceid):
        """Return True if the VM instanceid has been seen before.
        """
        cyvm = self.cdb.get_by_iaasid(instanceid)
        if cyvm:
            return True
        return False

    def get_run_vms_or_none(self, run_name):
        """Get list of VMs for a run name or return None"""

        if not self.cdb:
            raise ProgrammingError("cannot persist anything without setup/validation")
        cyvm_a = self.cdb.get_iaas_by_runname(run_name) 
        vm_a = []
        for cyvm in cyvm_a:
            rvm = RunVM()
            rvm.instanceid = cyvm.iaasid
            rvm.nodeid = cyvm.nodeid
            rvm.hostname = cyvm.hostname
            rvm.service_type = cyvm.service_type
            rvm.parent = cyvm.parent
            rvm.runlogdir = cyvm.runlogdir
            rvm.vmlogdir = cyvm.vmlogdir

            for e in cyvm.events:
                xtras = {}
                for x in e.extra:
                    xtras[x.key] = x.value
                c = CYvent(e.source, e.name, e.unique_event_key, e.timestamp, xtras)
                rvm.events.append(c)
            vm_a.append(rvm)

        return vm_a
