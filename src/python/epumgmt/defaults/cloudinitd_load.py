from epumgmt.api import RunVM
from epumgmt.api.exceptions import *
import cloudinitd
from cloudinitd.user_api import CloudInitD
from cloudinitd.exceptions import APIUsageException

def get_cloudinitd_service(cloudinitd, name):
    """Return the cloudinit.d service by exact name match or raise IncompatibleEnvironment"""
    
    if not cloudinitd:
        raise Exception("requires cloudinitd reference")
    if not name:
        raise Exception("requires service name")
    noservicemsg = "Cannot find the '%s' service in cloudinit.d run '%s'" % (name, cloudinitd.run_name)
    try:
        aservice = cloudinitd.get_service(name)
    except Exception, e:
        raise IncompatibleEnvironment("%s: %s" % (noservicemsg, str(e)))
    if not aservice:
        raise IncompatibleEnvironment(noservicemsg)
    return aservice

def service_callback(cb, cloudservice, action, msg):
    if action == cloudinitd.callback_action_error:
        cb._log.error("Problem with service %s: %s" % (cloudservice.name, msg))

def load_for_destruction(p, c, m, run_name, cloudinitd_dbdir):
    return CloudInitD(cloudinitd_dbdir, db_name=run_name,
                      terminate=True, boot=False, ready=False,
                      continue_on_error=True,
                      service_callback=service_callback, log=c.log)

def load(p, c, m, run_name, cloudinitd_dbdir, silent=False, terminate=False):
    """Load any EPU related instances from a local cloudinit.d launch with the same run name.
    """
    
    try:
        cb = CloudInitD(cloudinitd_dbdir, db_name=run_name, terminate=terminate, boot=False, ready=False)
    except APIUsageException, e:
        raise IncompatibleEnvironment("Problem loading records from cloudinit.d: %s" % str(e))
    svc_list = cb.get_all_services()

    count = 0
    for svc in svc_list:
        foundservice = None
        if svc.name.find("epu-") == 0:
            foundservice = svc.name
        elif svc.name.find("provisioner") == 0:
            foundservice = "provisioner"
        if foundservice:
            count += 1
            instance_id = svc.get_attr_from_bag("instance_id")
            hostname = svc.get_attr_from_bag("hostname")
            _load_host(p, c, m, run_name, instance_id, hostname, foundservice)

    if silent:
        return cb

    if not count:
        msg = "Services must be named 'svc-epu-*' or 'svc-provisioner' in order to be recognized."
        c.log.info("No EPU related services in the cloudinit.d '%s' launch. %s" % (run_name, msg))
    elif count == 1:
        c.log.info("One EPU related service in cloudinit.d '%s' launch" % run_name)
    else:
        c.log.info("%d EPU related services in the cloudinit.d '%s' launch" % (count, run_name))

    return cb

def _load_host(p, c, m, run_name, instanceid, hostname, servicename):
    """Load a VM instance from cloudinit information
    """

    vm = RunVM()
    vm.instanceid = instanceid
    vm.hostname = hostname
    vm.service_type = servicename

    m.runlogs.new_vm(vm)
    if m.persistence.new_vm(run_name, vm):
        c.log.info("New EPU related service detected: '%s'.  Instance ID is '%s', host '%s'" % (servicename, vm.instanceid, vm.hostname))

    return vm
