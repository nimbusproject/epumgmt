from epumgmt.api.exceptions import *
from epumgmt.main.em_core_load import get_cloudinit_for_destruction
import em_core_logfetch

def terminate(p, c, m, run_name, cloudinitd):
    """Destroy all VM instances that are part of the run.
    """

    m.remote_svc_adapter.initialize(m, run_name, cloudinitd)
    provisioner_kill = m.remote_svc_adapter.is_channel_open()

    if not provisioner_kill:
        c.log.warn("Problem with access to the services, cannot terminate workers without this channel")
        c.log.info("Killing only the cloudinit.d-launched nodes.")
    else:
        c.log.info("Terminating all workers in run '%s'" % run_name)
        if m.remote_svc_adapter.kill_all_workers():
            c.log.info("Terminated all workers in run '%s'" % run_name)
        else:
            c.log.error("Problem triggering worker termination, you need to make sure these are terminated manually!")
            c.log.info("Fetching provisioner logs")
            em_core_logfetch.fetch_by_service_name(p, c, m, run_name, "provisioner")
            c.log.info("Fetched provisioner logs")
            raise UnexpectedError("Problem triggering worker termination, you need to make sure these are terminated manually!")
        em_core_logfetch.fetch_by_service_name(p, c, m, run_name, "provisioner")

    c.log.info("Shutting down all services launched by cloudinit.d for '%s'" % run_name)
    # Need a different instantiation of cloudinitd for shutdown
    cloudinitd_terminate = get_cloudinit_for_destruction(p, c, m, run_name)
    cloudinitd_terminate.shutdown()
    cloudinitd_terminate.block_until_complete(poll_period=1.0)
    c.log.info("Shutdown all services launched by cloudinit.d for '%s'" % run_name)
