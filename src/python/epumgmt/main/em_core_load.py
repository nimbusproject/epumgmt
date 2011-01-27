from epumgmt.defaults import RunVM
from epumgmt.api.exceptions import *
from epumgmt.main import em_args
from cloudinitd.user_api import CloudInitD
import os
import os.path

def load(p, c, m, run_name):
    ci_path = self.p.get_arg_or_none(em_args.CLOUDINITD_DIR)
    if not ci_path:
        ci_path = os.path.expanduser("~/.cloudinit")

    cb = CloudInitD(ci_path, db_name=run_name, terminate=False, boot=False, ready=False)
    svc_list = cb.get_all_services()


    for svc in svc_list:
        if svc.name.find("epu-") == 0:
            instance_id = svc.get_attr_from_bag("instance_id")
            hostname = svc.get_attr_from_bag("hostname")
            load_host(p, c, m, run_name, instance_id, hostname, svc.name[4:])


def load_host(p, c, m, run_name, instanceid, hostname, servicename):
    """Load a VM instance from cloudinit information
    
    p,c,m are seen everywhere: parameters, common, modules 
    """
    if c.trace:
        c.log.debug("load_host()")
        
    vm = RunVM()
    vm.instanceid = instanceid
    vm.hostname = hostname
    vm.service_type = servicename
    
    m.runlogs.new_vm(vm)
    m.persistence.new_vm(run_name, vm)
    c.log.debug("persisted info about '%s', host '%s'" % (vm.instanceid, vm.hostname))
    
    return vm
