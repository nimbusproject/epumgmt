from epumgmt.defaults import RunVM
from epumgmt.api.exceptions import *
from epumgmt.main import em_args
from cloudinitd.user_api import CloudInitD
from cloudinitd.exceptions import APIUsageException
import os
import os.path

def load(p, c, m, run_name):
    ci_path = p.get_arg_or_none(em_args.CLOUDINITD_DIR)
    if not ci_path:
        ci_path = os.path.expanduser("~/.cloudinitd")

    try:
        cb = CloudInitD(ci_path, db_name=run_name, terminate=False, boot=False, ready=False)
    except APIUsageException, e:
        raise IncompatibleEnvironment("Problem loading records from cloudinit.d: %s" % str(e))
    svc_list = cb.get_all_services()

    count = 0
    for svc in svc_list:
        if svc.name.find("epu-") == 0 or svc.name.find("provisioner") == 0:
            instance_id = svc.get_attr_from_bag("instance_id")
            hostname = svc.get_attr_from_bag("hostname")
            load_host(p, c, m, run_name, instance_id, hostname, svc.name[4:])
            count += 1

    if not count:
        msg = "Services must be named 'svc-epu-*' or 'svc-provisioner' in order to be recognized."
        c.log.info("No EPU related services in the cloudinit.d '%s' launch. %s" % (run_name, msg))
    elif count == 1:
        c.log.info("One EPU related service in cloudinit.d '%s' launch" % run_name)
    else:
        c.log.info("%d EPU related services in the cloudinit.d '%s' launch" % (count, run_name))

def load_host(p, c, m, run_name, instanceid, hostname, servicename):
    """Load a VM instance from cloudinit information
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
        
    vm = RunVM()
    vm.instanceid = instanceid
    vm.hostname = hostname
    vm.service_type = servicename
    
    m.runlogs.new_vm(vm)
    if m.persistence.new_vm(run_name, vm):
        c.log.info("New EPU related service detected: '%s'.  Instance ID is '%s', host '%s'" % (servicename, vm.instanceid, vm.hostname))
    
    return vm
