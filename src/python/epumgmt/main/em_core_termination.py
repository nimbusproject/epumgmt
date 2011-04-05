from epumgmt.api.exceptions import *
from epumgmt.main.em_core_load import get_cloudinit_for_destruction
import time

def terminate(p, c, m, run_name, cloudinitd):
    """Destroy all VM instances that are part of the run.
    """

    m.remote_svc_adapter.initialize(m, run_name, cloudinitd)
    provisioner_kill = m.remote_svc_adapter.is_channel_open()

    if not provisioner_kill:
        c.log.warn("Problem with access to the services, cannot terminate workers without this channel")
        c.log.info("Killing only the cloudinit.d-launched nodes.")
    else:
        if not m.remote_svc_adapter.kill_all_workers():
            raise UnexpectedError("Problem triggering worker termination, you need to make sure these are terminated manually!")
        # TODO: here, we need to make sure the provisioner is done killing things with some mechanism like RPC.
        #       This will require some thought and design.  For now, this happens fairly instantly if
        #       the IaaS service is available, etc.  But we should know for sure before proceeding.
        c.log.info("Sent signal to the provisioner, waiting for it to terminate all workers in run '%s'" % run_name)
        time.sleep(5)

    # Need a different instantiation of cloudinitd for shutdown
    cloudinitd_terminate = get_cloudinit_for_destruction(p, c, m, run_name)
    cloudinitd_terminate.shutdown()
    cloudinitd_terminate.block_until_complete(poll_period=1.0)
    c.log.info("Shutdown all services launched by cloudinit.d for '%s'" % run_name)
