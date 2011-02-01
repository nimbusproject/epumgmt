import os

from epumgmt.api.exceptions import *
import epumgmt.main.em_args as em_args
from epumgmt.api.actions import ACTIONS

import child

class DefaultRunlogs:
    
    def __init__(self, params, common):
        self.p = params
        self.c = common
        self.validated = False
        self.thisrundir = None

        # temporary assumption that this is same on every VM, see events.conf
        self.allvmslogdir = None
    
    
    def validate(self):
        run_name = self.p.get_arg_or_none(em_args.NAME)
        
        runlogdir = self.p.get_conf_or_none("events", "runlogdir")
        if not runlogdir:
            raise InvalidConfig("There is no runlogdir configuration")
        
        if not os.path.isabs(runlogdir):
            runlogdir = self.c.resolve_var_dir(runlogdir)
        
        if not os.path.exists(runlogdir):
            raise InvalidConfig("The runlogdir does not exist: %s" % runlogdir)
        
        self.thisrundir = os.path.join(runlogdir, run_name)
        if not os.path.exists(self.thisrundir):
            os.mkdir(self.thisrundir)
            self.c.log.debug("Created a new directory for the logfiles generated on nodes in this run: %s" % self.thisrundir)
        else:
            self.c.log.debug("Directory of logfiles generated on nodes in this run: %s" % self.thisrundir)
        
        self.allvmslogdir = self.p.get_conf_or_none("events", "vmlogdir")
        if not self.allvmslogdir:
            raise InvalidConfig("There is no events:vmlogdir configuration")

        self.validated = True


    def new_vm(self, newvm):
        """Make the module aware of a new VM.
        It also will annotate the VM object.  It can handle a VM that has
        been through this process before, so no need to check for it.
        """
        
        if not self.validated:
            raise ProgrammingError("operation called without necessary validation")
            
        if not newvm.instanceid:
            raise ProgrammingError("Cannot determine VM instance ID")
            
        thisvm_runlog_dir = os.path.join(self.thisrundir, newvm.instanceid)
            
        if newvm.runlogdir:
            if newvm.runlogdir != thisvm_runlog_dir:
                self.c.log.warn("The runlog directory for the VM was recorded but it is not what we would expect (%s != %s)" % (newvm.runlogdir, thisvm_runlog_dir))
        elif not os.path.exists(thisvm_runlog_dir):
            os.mkdir(thisvm_runlog_dir)
            newvm.runlogdir = thisvm_runlog_dir
            self.c.log.debug("created runlog directory for this instance: %s" % thisvm_runlog_dir)
        else:
            newvm.runlogdir = thisvm_runlog_dir
            
        if not os.path.exists(newvm.runlogdir):
            raise IncompatibleEnvironment("Could not find the runlog directory: %s" % newvm.runlogdir)
        
        newvm.vmlogdir = self.allvmslogdir

    def _cloudinitd_service(self, cloudinitd, name):
        """Return the cloudinit.d service by exact name match or raise IncompatibleEnvironment"""
        noservicemsg = "Cannot find the '%s' service in cloudinit.d run '%s'" % (name, cloudinitd.run_name)
        try:
            aservice = cloudinitd.get_service(name)
        except Exception, e:
            raise IncompatibleEnvironment("%s: %s" % (noservicemsg, str(e)))
        if not aservice:
            raise IncompatibleEnvironment(noservicemsg)
        return aservice

    def get_scp_command_str(self, c, vm, cloudinitd):
        if not vm.hostname:
            c.log.warn("Cannot retrieve logs for '%s', hostname is unknown" % vm.instanceid)
            return None

        # SCP command for workers will be presumed the same as svc-provisioner.
        try:
            provisioner = cloudinitd.get_service("provisioner")
        except IncompatibleEnvironment, e:
            raise IncompatibleEnvironment("Problem finding the provisioner node in cloudinit.d, "
                                          "cannot fetch any worker logs without it: %s" % str(e))

        source = vm.vmlogdir
        dest = vm.runlogdir
        forcehost = None
        try:
            svc = self._cloudinitd_service(cloudinitd, vm.service_type)
        except IncompatibleEnvironment:
            if vm.service_type.find("-worker") < 0:
                c.log.warn("cloudinit.d is unaware of '%s' but it is not an EPU worker?" % vm.service_type)
            svc = provisioner
            forcehost = vm.hostname
        return svc.get_scp_command(source, dest, recursive=True, forcehost=forcehost)
        
    def fetch_logs(self, scpcmd):
        if not self.validated:
            raise ProgrammingError("operation called without necessary validation")
        self._run_one_cmd(scpcmd)

    def _run_one_cmd(self, cmd):
        self.c.log.debug("command = '%s'" % cmd)
        timeout = 30.0 # seconds
        (killed, retcode, stdout, stderr) = child.child(cmd, timeout=timeout)
        
        if killed:
            self.c.log.error("TIMED OUT: '%s'" % cmd)
            return False
        
        if retcode == 0:
            self.c.log.debug("command succeeded: '%s'" % cmd)
            return True
        else:
            errmsg = "problem running command, "
            if retcode < 0:
                errmsg += "killed by signal:"
            if retcode > 0:
                errmsg += "exited non-zero:"
            errmsg += "'%s' ::: return code" % cmd
            errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (retcode, stdout, stderr)
            
            # these commands will commonly fail 
            if self.c.trace:
                self.c.log.debug(errmsg)
            return False
