import os

import epumgmt.main.em_core_load
import epumgmt.defaults.child


# used to fetch torque logs on torque headnode
class TorqueLogs:
    def __init__(self, p, c, m, run_name):
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name

        # hardcoded, though it is the default location
        self.server_log_dirs = ['/var/spool/torque/server_logs/']
        self.cloudinitd = epumgmt.main.em_core_load.get_cloudinit(p, c, m, run_name)
        self.svc = self.cloudinitd.get_service("rabbit")

        runlogdir = p.get_conf_or_none("events", "runlogdir")
        if not runlogdir:
            raise InvalidConfig("There is no runlogdir configuration")
        if not os.path.isabs(runlogdir):
            runlogdir = self.c.resolve_var_dir(runlogdir)

        tld = os.path.join(runlogdir, run_name)
        self.torquelogdir = os.path.join(tld, "torque-server_logs")

        if not os.path.exists(self.torquelogdir):
            self.c.log.debug("Creating directory: %s" % self.torquelogdir)
            os.mkdir(self.torquelogdir)

    def _execute_cmd(self, cmd):
        self.c.log.debug("command = '%s'" % cmd)
        timeout = 30.0 # seconds
        (k, rc, out, err) = epumgmt.defaults.child.child(cmd, timeout=timeout)

        if k:
            self.c.log.error("TIMED OUT: '%s'" % cmd)
            return False

        if not rc:
            self.c.log.debug("command succeeded: '%s'" % cmd)
            return True
        else:
            errmsg = "problem running command, "
            if rc < 0:
                errmsg += "killed by signal:"
            if rc > 0:
                errmsg += "exited non-zero:"
            errmsg += "'%s' ::: return code" % cmd
            errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (rc, out, err)

            # these commands will commonly fail
            if self.c.trace:
                self.c.log.debug(errmsg)
            return False

    def fetch(self):
        for log_dir in self.server_log_dirs:
            logs = os.path.join(log_dir, "*")
            cmd = self.svc.get_scp_command(logs, self.torquelogdir)
            return self._execute_cmd(cmd)


def fetch_logs(p, c, m, run_name):
    c.log.info("Fetching torque logs")
    logs = TorqueLogs(p, c, m, run_name)
    if not logs.fetch():
        c.log.error("Failed to fetch Torque logs")
    else:
        c.log.info("Torque logs have been retrieved")
