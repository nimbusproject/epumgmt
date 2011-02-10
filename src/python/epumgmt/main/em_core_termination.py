from epumgmt.api.exceptions import *
import epumgmt.defaults.child as child
from epumgmt.main.em_core_load import get_cloudinit_for_destruction
import os
import time

def terminate(p, c, m, run_name):
    """Destroy all VM instances that are part of the run.
    
    p,c,m are seen everywhere: parameters, common, modules 
    """

    if c.trace:
        c.log.debug("terminate()")

    cloudinitd = get_cloudinit_for_destruction(p, c, m, run_name)

    # First, instruct the provisioner to kill all the nodes.
    try:
        provisioner = cloudinitd.get_service("provisioner")
    except IncompatibleEnvironment, e:
        raise IncompatibleEnvironment("Problem finding the provisioner node in cloudinit.d, "
                                      "cannot terminate workers without it: %s" % str(e))

    cmd = provisioner.get_ssh_command()

    # TODO: generalize
    cmd += " 'cd /home/cc/ioncore-python && sudo ./start-killer.sh'"

    if not _run_one_cmd(c, cmd):
        raise UnexpectedError("Problem triggering worker termination via the provisioner node, "
                                      "you need to make sure these are terminated manually!")

    # TODO: here, we need to make sure the provisioner is done killing things with some mechanism.
    #       This will require some thought and design.  For now, this happens fairly instantly if
    #       the IaaS service is available, etc.  But we should know for sure before proceeding.

    c.log.info("Sent signal to the provisioner, waiting for it to terminate all workers in run '%s'" % run_name)
    time.sleep(5)

    cloudinitd.shutdown()
    cloudinitd.block_until_complete(poll_period=1.0)
    c.log.info("Shutdown all services launched by cloudinit.d for '%s'" % run_name)

def _run_one_cmd(c, cmd):
    c.log.debug("command = '%s'" % cmd)
    timeout = 30.0 # seconds
    (killed, retcode, stdout, stderr) = child.child(cmd, timeout=timeout)

    if killed:
        c.log.error("TIMED OUT: '%s'" % cmd)
        return False

    if retcode == 0:
        c.log.debug("command succeeded: '%s'" % cmd)
        return True
    else:
        errmsg = "problem running command, "
        if retcode < 0:
            errmsg += "killed by signal:"
        if retcode > 0:
            errmsg += "exited non-zero:"
        errmsg += "'%s' ::: return code" % cmd
        errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (retcode, stdout, stderr)
        c.log.error(errmsg)
        return False
