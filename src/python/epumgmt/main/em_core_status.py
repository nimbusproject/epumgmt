import uuid
from datetime import datetime

from cloudyvents.cyvents import CYvent
import em_core_findworkers
from epumgmt.api import RunVM
from epumgmt.main import em_args
from epumgmt.api.exceptions import IncompatibleEnvironment, ProgrammingError

def find_latest_status(p, c, m, run_name, cloudinitd, findworkersfirst=True):
    """Finds new workers, EPU controllers, and gathers all the information possible for status

    The information is all stored to the RunVM objects in persistence

    Return "allvms" for convenience, a list of RunVM instances
    """
    if findworkersfirst:
        try:
            em_core_findworkers.find_once(p, c, m, run_name)
        except IncompatibleEnvironment,e:
            c.log.error("Problem finding new workers: %s" % str(e))
    allvms = m.persistence.get_run_vms_or_none(run_name)
    if not allvms or len(allvms) == 0:
        raise IncompatibleEnvironment("Cannot find any VMs associated with run '%s'" % run_name)

    _find_latest_turtle_status(c, m, run_name, cloudinitd, allvms)
    _find_latest_worker_status(c, m, run_name, cloudinitd, allvms)

    return allvms

def pretty_status(p, c, m, run_name, cloudinitd):
    """Log information about VM instances that are part of the run.

    To update or not is based on a given parameter to the program.
    
    If you are interested in using a more API-like method, see find_latest_status()
    """

    c.log.debug("Obtaining status")

    no_update = p.get_arg_or_none(em_args.STATUS_NOUPDATE)

    if no_update:
        c.log.debug("The %s flag is suppressing status update" % em_args.STATUS_NOUPDATE.long_syntax)
    else:
        c.log.info("Getting the latest status information")
        find_latest_status(p, c, m, run_name, cloudinitd)

# ----------------------------------------------------------------------------------------------------
# IMPL
# ----------------------------------------------------------------------------------------------------

def _print_workers(c, m, allvms):
    return


def _print_services(c, m, allvms):
    pass

def _find_latest_worker_status(c, m, run_name, cloudinitd, allvms):
    """Update what can be found for any nodes launched via EPU controllers
    """

    c.log.info("Updating worker status")

    # Print each new info item
    trace = False

    m.remote_svc_adapter.initialize(m, run_name, cloudinitd)
    if not m.remote_svc_adapter.is_channel_open():
        c.log.warn("Cannot get worker status: there is no channel open to the EPU controllers")
        return

    controller_map = m.remote_svc_adapter.controller_map(allvms)
    if not len(controller_map):
        c.log.warn("Cannot get worker status: there is a channel to the EPU controllers but no controllers are configured")
        return
    
    controllers = []
    for instanceid in controller_map.keys():
        controllers.extend(controller_map[instanceid])

    provisioner_vm = None
    for vm in allvms:
        if vm.service_type == "provisioner":
            provisioner_vm = vm
            break
    if not provisioner_vm:
        # This is an exception because it should be there especially if is_channel_open() passed above
        raise ProgrammingError("Cannot update worker status without provisioner channel into the system")

    controller_state_map = m.remote_svc_adapter.worker_state(controllers, provisioner_vm)

    # Generate "iaas_state" and "heartbeat_state" cloudyvents.  Discover worker 'parent' in the process.
    for controller in controllers:
        state = controller_state_map[controller]
        for wis in state.instances:
            vm = _get_vm_with_nodeid(wis.nodeid, allvms)
            if not vm:
                # Can't make a RunVM yet for this, unfortunately
                c.log.warn("Controller '%s' knows about worker we have no IaaS id for yet: %s" % (controller, wis.nodeid))
                continue
            
            newparent = False
            if not vm.parent:
                vm.parent = controller
                newparent = True
            elif vm.parent != controller:
                raise ProgrammingError("Previous RunVM had a different parent "
                        "'%s', new status query indicates parent is '%s'" % (vm.parent, controller))

            newevent = _get_events_from_wis(wis, vm, controller, trace, c)
            
            if newevent or newparent:
                m.persistence.store_run_vms(run_name, [vm])

    # Generate "de_state", "de_conf_report", and "last_queuelen_size" cloudyvents.
    for instanceid in controller_map.keys():
        vm = _get_vm_with_instanceid(instanceid, allvms)
        if not vm:
            raise ProgrammingError("instanceid in RunVMs that is not in controller_map?")

        any_newevent = False
        controllers = controller_map[instanceid]
        for controller in controllers:
            state = controller_state_map[controller]
            newevent = _get_events_from_controller_state(state, vm, controller, trace, c)
            if newevent:
                any_newevent = True

        if any_newevent:
            m.persistence.store_run_vms(run_name, [vm])


def _get_events_from_wis(wis, vm, controller, trace, c):
    """See if there is anything in the WorkerInstanceState, return True if events were added
    """
    newevent = False

    if wis.iaas_state:
        event = CYvent(controller,
                       "iaas_state",
                       str(uuid.uuid4()),
                       datetime.fromtimestamp(wis.iaas_state_time),
                       extra={"nodeid":wis.nodeid,
                              "state":wis.iaas_state,
                              "instanceid": vm.instanceid})
        vm.events.append(event)
        newevent = True
        if trace:
            c.log.debug("iaas_state for %s: %s (from controller '%s')" % (vm.instanceid, wis.iaas_state, controller))

    if wis.heartbeat_state:
        event = CYvent(controller,
                       "heartbeat_state",
                       str(uuid.uuid4()),
                       datetime.fromtimestamp(wis.heartbeat_time),
                       extra={"nodeid":wis.nodeid,
                              "state":wis.heartbeat_state,
                              "instanceid": vm.instanceid})
        vm.events.append(event)
        newevent = True
        if trace:
            c.log.debug("heartbeat_state for %s: %s (from controller '%s')" % (vm.instanceid, wis.heartbeat_state, controller))

    return newevent


def _get_events_from_controller_state(state, vm, controller, trace, c):
    """See if there is anything in the EPUControllerState, return True if any events were added
    """
    newevent = False

    if state.de_state:
        event = CYvent(controller,
                       "de_state",
                       str(uuid.uuid4()),
                       datetime.fromtimestamp(state.capture_time),
                       extra={"de_state": state.de_state})
        vm.events.append(event)
        newevent = True
        if trace:
            c.log.debug("de_state for controller %s: %s" % (controller, state.de_state))

    if state.de_conf_report:
        event = CYvent(controller,
                       "de_conf_report",
                       str(uuid.uuid4()),
                       datetime.fromtimestamp(state.capture_time),
                       extra={"de_conf_report": state.de_conf_report})
        vm.events.append(event)
        newevent = True
        if trace:
            c.log.debug("de_conf_report for controller %s: %s" % (controller, state.de_conf_report))

    if state.last_queuelen_size >= 0:
        event = CYvent(controller,
                       "last_queuelen_size",
                       str(uuid.uuid4()),
                       datetime.fromtimestamp(state.last_queuelen_time),
                       extra={"last_queuelen_size": state.last_queuelen_size})
        vm.events.append(event)
        newevent = True
        if trace:
            c.log.debug("last_queuelen_size for controller %s: %s" % (controller, state.last_queuelen_size))

    return newevent

def _get_vm_with_nodeid(nodeid, allvms):
    """Return RunVM object for nodeid or None if not found
    """
    for vm in allvms:
        if vm.nodeid == nodeid:
            return vm
    return None

def _get_vm_with_instanceid(instanceid, allvms):
    """Return RunVM object for instanceid or None if not found
    """
    for vm in allvms:
        if vm.instanceid == instanceid:
            return vm
    return None

def _find_latest_turtle_status(c, m, run_name, cloudinitd, allvms):
    """Update what can be updated for any nodes in the "bottom turtle" layer, i.e., launched via the launch plan.
    """
    
    return # Waiting on cloudinitd API

    # The launch plan service list was already obtained by way of the cloudinit_load.load() call.
    # Here, we look for any non-worker and attempt to get the iaas status

    #vms = _filter_out_workers(allvms)
    #for vm in vms:
    #    svc = cloudinitd.get_service(vm.service_type)

def _filter_out_workers(allvms):

    # We are currently in a transition state, the WORKER_SUFFIX idea is being obsoleted
    # by a direct "parent_epu_controller" instance variable in RunVM

    nonworkers = []
    for vm in allvms:
        if vm.parent_epu_controller:
            # If parent_epu_controller is listed, it must be a worker
            continue
        elif vm.service_type.endswith(RunVM.WORKER_SUFFIX):
            # For now, to be backwards compatible, WORKER_SUFFIX suffix signals a worker
            continue
        nonworkers.append(vm)
    return nonworkers
