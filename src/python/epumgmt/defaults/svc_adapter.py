from epumgmt.api import EPUControllerState, WorkerInstanceState, RunVM
from epumgmt.defaults.cloudinitd_load import get_cloudinitd_service
from epumgmt.defaults.child import child
from epumgmt.api.exceptions import *
from datetime import timedelta
import epustates
import os
import json
import time
import uuid

class DefaultRemoteSvcAdapter:

    def __init__(self, params, common):
        self.p = params
        self.c = common

        self.initialized = False

        # Filled by initialization method
        self.m = None
        self.run_name = None
        self.controller_prefix = None
        self.cloudinitd = None
        self.homedir = None
        self.envfile = None

        # These may or may not be present at a given time
        self.provisioner = None

    def validate(self):
        pass

    def initialize(self, m, run_name, cloudinitd):

        if self.initialized:
            return

        if not m:
            raise ProgrammingError("no Modules")
        if not run_name:
            raise ProgrammingError("no run name")
        if not cloudinitd:
            raise ProgrammingError("no cloudinitd")

        self.m = m
        self.run_name = run_name
        self.cloudinitd = cloudinitd

        self.controller_prefix = self.p.get_conf_or_none("svcadapter", "controller_prefix")
        if not self.controller_prefix:
            raise InvalidConfig("Missing configuration: [svcadapter] -> controller_prefix")

        self.homedir = self.p.get_conf_or_none("svcadapter", "homedir")
        if not self.homedir:
            raise InvalidConfig("Missing configuration: [svcadapter] -> homedir")

        self.envfile = self.p.get_conf_or_none("svcadapter", "envfile")
        if not self.envfile:
            raise InvalidConfig("Missing configuration: [svcadapter] -> envfile")
        
        self.initialized = True

    def is_channel_open(self):
        """Return True if there is a way to interact with the services
        """
        self._check_init()
        try:
            self._get_provisioner()
        except Exception:
            self.c.log.exception("Problem locating 'provisioner'")
            return False
        return True

    def kill_all_workers(self):
        """Return True if the kill command was successfully sent, False if there was an issue
        """
        self._check_init()
        if not self.is_channel_open():
            raise IncompatibleEnvironment("Cannot kill without an open channel to the services")

        cmd = self._get_provisioner().get_ssh_command()
        cmd += " " + self._get_epu_script_cmd("epu-killer")
        return self._run_one_cmd(cmd)

    def kill_workers(self, node_id_list):
        """Return True if the kill command was successfully sent, False if there was an issue

        node_id_list -- nonempty list of EPU node IDs to kill
        """
        self._check_init()
        if not self.is_channel_open():
            raise IncompatibleEnvironment("Cannot kill without an open channel to the services")

        if not len(node_id_list):
            raise Exception("Empty node ID list")
        cmd = self._get_provisioner().get_ssh_command()
        cmd += ' ' + self._get_epu_script_cmd("epu-killer", extras=node_id_list)
        return self._run_one_cmd(cmd)

    def reconfigure_n(self, controller, newn):
        """Return True if the reconfigure command was sent, False if there was an issue

        controller -- controller service name to send to
        newn -- integer for new N
        """
        self._check_init()
        if not self.is_channel_open():
            raise IncompatibleEnvironment("Cannot kill without an open channel to the services")

        extra_args = [controller, newn]
        cmd = self._get_provisioner().get_ssh_command()
        cmd += ' ' + self._get_epu_script_cmd("epu-reconfigure-n", extras=extra_args)
        return self._run_one_cmd(cmd)

    def worker_state(self, controllers, provisioner_vm):
        """Contact EPU controller(s) and find worker state.

        controllers -- nonempty list of EPU controller service names

        provisioner_vm -- RunVM for the provisioner node, our channel into the state retrieval

        Returns dictionary of { controller_name -> EPUControllerState instance }

        Raise Exception if state retrieval fails
        """

        if not provisioner_vm:
            raise IncompatibleEnvironment("Cannot update status without provisioner node, the channel into the system")

        self._check_init()
        if not self.is_channel_open():
            raise IncompatibleEnvironment("Cannot get worker state without an open channel to the services")

        if not len(controllers):
            raise InvalidInput("Empty controllers service name list")

        filename = "epu-worker-state-%s" % str(uuid.uuid4())
        remote_filename = "%s/logs/%s" % (self.homedir, filename)

        extra_args = [remote_filename]
        extra_args.extend(controllers)
        cmd = self._get_provisioner().get_ssh_command()
        cmd += ' ' + self._get_epu_script_cmd("epu-state", extras=extra_args)
        if not self._run_one_cmd(cmd):
            raise UnexpectedError("Could not run state query")

        return self._intake_query_result(provisioner_vm, filename, remote_filename)

    def controller_map(self, allvms):
        """Returns dictionary of { instanceid --> list of controller service addressess }
        """
        self._check_init()

        retdict = {}
        for vm in allvms:
            if not vm.service_type:
                continue
            try:
                newctrls = self._find_controllers_from_svc(vm.service_type)
                for controller in newctrls:
                    self.c.log.debug("Found controller (svc '%s'): %s" % (vm.service_type, controller))
                retdict[vm.instanceid] = newctrls
            except Exception, e:
                if not vm.service_type.endswith(RunVM.WORKER_SUFFIX):
                    self.c.log.debug("Issue with finding EPU controllers in %s: %s" % (vm.service_type, str(e)))
        return retdict

    def filter_by_controller(self, vm_list, controller):
        """Remove VMs from this list that do not have the controller as parent
        """
        if not vm_list:
            return []
        ok = []
        for vm in vm_list:
            if vm.parent == controller:
                ok.append(vm)
        return ok

    def filter_by_running(self, vm_list, include_pending=False):
        """Remove VMs from this list that we know are not directly contactable because they are terminated
        or still booting.

        include_pending -- Include VMs that are still being requested or propagating
        """
        if not vm_list:
            return []
        ok = []
        for vm in vm_list:
            if self.running_iaas_status(vm, include_pending=include_pending):
                ok.append(vm)
        return ok

    def running_iaas_status(self, vm, include_pending=False):
        """Return True if the status of the VM means it can be interacted with (e.g. for logs)

        include_pending -- Include VMs that are still being requested or propagating
        """
        if not vm or not vm.instanceid:
            raise ProgrammingError("VM required and required to have instanceid: %s" % vm)

        latest = self.latest_iaas_status(vm)
        if not latest:
            # We don't have IaaS info for the "turtle" VMs yet: they default to True
            return True
        if latest in [epustates.STARTED, epustates.RUNNING]:
            return True
        if include_pending:
            if latest in [epustates.PENDING, epustates.ERROR_RETRYING, epustates.REQUESTED, epustates.REQUESTING]:
                return True
        return False

    def latest_iaas_status(self, vm):
        """Return iaas status or None if it cannot be determined
        """
        if not vm or not vm.instanceid:
            raise ProgrammingError("VM required and required to have instanceid: %s" % vm)

        # todo: switch to SQL query. There are far bigger performance issues in other parts
        d = timedelta(minutes=0)
        latest = None
        for ev in vm.events:
            if ev.name == "iaas_state":
                if not latest:
                    latest = ev
                elif (ev.timestamp - latest.timestamp) > d:
                    latest = ev
        if not latest:
            return None
        if not latest.extra or not latest.extra.has_key("state"):
            raise ProgrammingError("iaas_state event has unexpected structure: %s" % latest.extra)
        return latest.extra["state"]


    # ----------------------------------------------------------------------------------------------------
    # IMPL methods
    # ----------------------------------------------------------------------------------------------------

    def _check_init(self):
        if not self.initialized:
            raise ProgrammingError("You can not use this module without initializing it")

    def _find_controllers_from_svc(self, service_type):
        """Return a list of service contact addresses for all the EPU controllers in this
        cloudinit.d "svc" that was launched.
        """
        svc = get_cloudinitd_service(self.cloudinitd, service_type)
        allkeys = svc.get_keys_from_bag()
        controllers = []
        for key in allkeys:
            if key.startswith(self.controller_prefix):
                controllers.append(svc.get_attr_from_bag(key))
        return controllers

    def _get_provisioner(self):
        """Try to locate something in the run called "provisioner".  This is our backdoor
        into the system (but only currently: this is not the best, final solution).

        Return provisioner svc
        
        Raises an Exception if it is not found.
        """
        if not self.provisioner:
            try:
                self.provisioner = self.cloudinitd.get_service("provisioner")
            except Exception:
                self.c.log.exception("Cannot locate provisioner:")
                raise
            if not self.provisioner:
                raise IncompatibleEnvironment("Cannot locate provisioner")
        return self.provisioner

    def _get_epu_script_cmd(self, script, extras=None):
        """ This tight coupling is one of the main reasons the current backdoor to the system is not best solution"""

        cmd = "'cd %s && sudo ./scripts/run_under_env.sh %s " % (self.homedir, self.envfile)
        cmd += "./scripts/%s messaging.conf" % script
        if extras:
            for extra in extras:
                cmd += " %s" % extra.strip()
        return "%s'" % cmd

    def  _run_one_cmd(self, cmd):
        self.c.log.debug("command = '%s'" % cmd)
        timeout = 30.0 # seconds
        (killed, retcode, stdout, stderr) = child(cmd, timeout=timeout)

        if killed:
            self.c.log.error("TIMED OUT: '%s'" % cmd)
            return False

        if not retcode:
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
            self.c.log.error(errmsg)
            return False

    def _intake_query_result(self, provisioner_vm, filename, remote_filename):
        """Returns dictionary of { controller_name -> EPUControllerState instance }
        """

        scpcmd = self.m.runlogs.get_onefile_scp_command_str(self.c, provisioner_vm, self.cloudinitd, remote_filename)
        if not self._run_one_cmd(scpcmd):
            raise UnexpectedError("Could not obtain state query result")

        local_filename = os.path.join(provisioner_vm.runlogdir, filename)
        if os.path.exists(local_filename):
            self.c.log.debug("State query result: %s" % local_filename)
        else:
            raise UnexpectedError("Expecting to find the state query result here: %s" % local_filename)

        return self._intake_query_result_from_file(local_filename)

    def _intake_query_result_from_file(self, local_filename):
        """Returns dictionary of { controller_name -> EPUControllerState instance }
        """
        f = open(local_filename)
        result = json.load(f)
        f.close()

        controller_state_map = {}

        controllers = result.keys()
        for controller in controllers:
            info = result[controller]
            state = EPUControllerState()
            controller_state_map[controller] = state
            
            state.capture_time = int(time.time())
            state.de_state = info['de_state']
            state.de_conf_report = info['de_conf_report']
            state.controller_name = controller
            state.last_queuelen_size = int(info['last_queuelen_size'])
            state.last_queuelen_time = int(info['last_queuelen_time'])
            
            state.instances = []
            for nodeid in info['instances'].keys():
                wis = WorkerInstanceState()
                state.instances.append(wis)
                
                wis.parent_controller = controller
                wis.nodeid = nodeid
                wis.iaas_state = info['instances'][nodeid]['iaas_state']
                iaas_state_time = info['instances'][nodeid]['iaas_state_time']
                wis.iaas_state_time = int(iaas_state_time)

                wis.hearbeat_state = info['instances'][nodeid]['hearbeat_state']
                heartbeat_time = info['instances'][nodeid]['heartbeat_time']
                wis.heartbeat_time = int(heartbeat_time)

        return controller_state_map
