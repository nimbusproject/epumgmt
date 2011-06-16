from optparse import Values

import os
import time
import json
import urllib2
import datetime
import threading
import tempfile

from epumgmt.defaults.log_events import AmqpEvents, TorqueEvents
from epumgmt.main.em_core_load import get_cloudinit_for_destruction
import epumgmt.main.em_core
import epumgmt.main.em_core_load
import epumgmt.defaults.child


# just used for logging events for starting / terminating the EPU controller
class EPUController:
    def __init__(self, p, c, m, run_name):
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name

        runlogdir = self.p.get_conf_or_none("events", "runlogdir")
        if not runlogdir:
            raise InvalidConfig("There is no runlogdir configuration")
        if not os.path.isabs(runlogdir):
            runlogdir = self.c.resolve_var_dir(runlogdir)

        tld = os.path.join(runlogdir, run_name)
        self.controllerlogdir = os.path.join(tld, "epucontrollerkill_logs")

        if not os.path.exists(self.controllerlogdir):
            self.c.log.debug("Creating directory: %s" % self.controllerlogdir)
            os.mkdir(self.controllerlogdir)

        self.controllerlog = os.path.join(self.controllerlogdir, 'controllerkill.log')

    def _log_event(self, event):
        lf = open(self.controllerlog, 'a')
        lf.write(event)
        lf.write('\n')
        lf.close()

    def _get_log_time(self):
        now = datetime.datetime.utcnow()
        return str(now)

    def start(self, num=1):
        start_time = self._get_log_time()
        for i in range(num):
            event = 'EPU_CONTROLLER_START %s' % start_time
            self._log_event(event)

    def terminate(self, num=1):
        end_time = self._get_log_time()
        for i in range(num):
            event = 'EPU_CONTROLLER_TERMINATE %s' % end_time
            self._log_event(event)


class Torque:
    def __init__(self, p, c, m, run_name, cloudinitd):
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name
        self.svc = cloudinitd.get_service("basenode")

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

    def _copy_file(self, filename):
        basename = os.path.basename(filename)
        cmd = self.svc.get_scp_command(filename, "/tmp", upload=True)
        if self._execute_cmd(cmd):
            ssh_cmd = self.svc.get_ssh_command()
            # scp command uses a different user then ssh and permissions set u+rw
            fix_cmd = "sudo chmod ugo+r /tmp/%s" % basename
            cmd = "%s '%s'" % (ssh_cmd, fix_cmd)
            return self._execute_cmd(cmd)
        return False

    def _qsub_job(self, basename):
        ssh_cmd = self.svc.get_ssh_command()
        submit_cmd = "qsub /tmp/%s" % basename
        cmd = "%s '%s'" % (ssh_cmd, submit_cmd)
        return self._execute_cmd(cmd)

    def submit(self, job):
        tf = tempfile.NamedTemporaryFile(delete=False)
        tf.write("sleep %s\n" % job.sleepsec)
        tf.close()

        if not self._copy_file(tf.name):
            self.c.log.error("Failed to copy job file, skipping submission")
        else:
            basename = os.path.basename(tf.name)
            for count in range(job.count):
                if not self._qsub_job(basename):
                    self.c.log.error("Failed to submit job")
                else:
                    self.c.log.debug("Job submitted successfully")

        try:
            os.remove(tf.name)
            self.c.log.debug("Removed temporary file: %s" % tf.name)
        except:
            self.c.log.error("Could not remove temporary file: %s" % tf.name)


class AMQP:
    def __init__(self, p, c, m, run_name, host, port):
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name
        self.host = host
        self.port = port
        self.submit_str = 'http://%s:%s/%s/%s/%s/%s'

    def submit(self, job):
        testName = '%s-jobs' % self.run_name
        submitStr = self.submit_str % (self.host, \
                                       self.port, \
                                       testName, \
                                       job.batchid, \
                                       job.count, \
                                       job.sleepsec)
        self.c.log.debug('submit: %s', submitStr)

        retry = 3
        while retry > 0:
            try:
                urllib2.urlopen(submitStr, timeout=180)
                retry = 0
            except Exception as e:
                self.c.log.error('Failed to submit task at %s' % job.startsec)
                self.c.log.error('Exception: %s' % e)
                retry -= 1


class WorkItem:
    def __init__(self, startsec, count, sleepsec=None, batchid=0):
        self.startsec = startsec
        self.count = count
        self.sleepsec = sleepsec
        self.batchid = batchid


class Workload:
    def __init__(self, \
                 key, \
                 p, \
                 c, \
                 m, \
                 run_name, \
                 workloadfilename, \
                 workloadtype, \
                 epucontroller=None):
        self.items = []
        self.threads = []
        self.key = key
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name
        self.workload_type = workloadtype
        self.cloudinitd = epumgmt.main.em_core_load.get_cloudinit(p, c, m, run_name)
        self.epucontroller = epucontroller
        # hardcoded for now, ick -- is this in a config somewhere?
        self.port = '8001'
        if self.workload_type == 'torque':
            self.host = self._get_hostname('epu-onesleeper')
        else:
            self.host = self._get_hostname('epu-onesleeper')

        if workloadfilename:
            workloadfilename = os.path.expanduser(workloadfilename)
            workloadfilename = os.path.abspath(workloadfilename)

            if os.path.exists(workloadfilename):
                try:
                    workloadfile = open(workloadfilename, 'r')
                    try:
                        for line in workloadfile:
                            self._add_line(line)
                    finally:
                        workloadfile.close()
                except IOError:
                    self.c.log.error('Failed to open and read from file: ' + \
                                     '%s' % workloadfilename)

    def _add_line(self, line):
        splitline = line.split()
        if self.key in [item.strip() for item in splitline]:
            if len(splitline) == 3:
                try:
                    linekey = splitline[0].strip()
                    startsec = int(splitline[1].strip())
                    count = int(splitline[2].strip())
                    item = WorkItem(startsec, count)
                    self.items.append(item)
                except Exception as e:
                    self.c.log.warn('Problem parsing line in workload ' + \
                                    'definition file: %s.' % line)
                    self.c.log.warn('Exception: %s' % e)
            elif len(splitline) == 5:
                try:
                    linekey = splitline[0].strip()
                    startsec = int(splitline[1].strip())
                    count = int(splitline[2].strip())
                    sleepsec = int(splitline[3].strip())
                    batchid = int(splitline[4].strip())
                    item = WorkItem(startsec, count, sleepsec, batchid)
                    self.items.append(item)
                except Exception as e:
                    self.c.log.warn('Problem parsing line in workload ' + \
                                    'definition file: %s.' % line)
                    self.c.log.warn('Exception: %s' % e)
            else:
                self.c.log.warn('Problem parsing line in workload ' + \
                                'definition file: %s.' % line)

    def _get_hostname(self, name):
        vms = self.m.persistence.get_run_vms_or_none(self.run_name)
        host = ''
        for vm in vms:
            if vm.service_type == name:
                host = vm.hostname
        return host

    def _find_workers(self):
        np = self.p
        np.optdict['action'] = 'find-workers'
        nopts = _build_opts_from_dict(np.optdict)
        eopts = epumgmt.main.em_core.EPUMgmtOpts(self.run_name,
                                                 self.p.optdict['conf'],
                                                 nopts)
        epumgmt.main.em_core.core(eopts)

    def _fetch_torque_logs(self):
        np = self.p
        np.optdict['action'] = 'torque-logfetch'
        nopts = _build_opts_from_dict(np.optdict)
        eopts = epumgmt.main.em_core.EPUMgmtOpts(self.run_name,
                                                 self.p.optdict['conf'],
                                                 nopts)
        epumgmt.main.em_core.core(eopts)

    def _fetch_logs(self):
        np = self.p
        np.optdict['action'] = 'logfetch'
        nopts = _build_opts_from_dict(np.optdict)
        eopts = epumgmt.main.em_core.EPUMgmtOpts(self.run_name,
                                                 self.p.optdict['conf'],
                                                 nopts)
        epumgmt.main.em_core.core(eopts)

    def _get_total_items(self):
        total = 0
        for item in self.items:
            total += item.count
        return total

    def execute(self):
        for item in self.items:
            t = None
            if self.key == 'KILL':
                t_args = [self.p, \
                          self.c, \
                          self.m, \
                          self.run_name, \
                          item.startsec, \
                          self.items]
                t = threading.Timer(item.startsec, \
                                     _kill_vms, \
                                     t_args)
            elif self.key == 'KILL_CONTROLLER':
                t_args = [self.p, \
                          self.c, \
                          self.m, \
                          self.run_name, \
                          item.startsec, \
                          self.cloudinitd, \
                          self.epucontroller]
                t = threading.Timer(item.startsec, \
                                     _kill_controller, \
                                     t_args)
            elif self.key == 'SUBMIT':
                t_args = [self.p, \
                          self.c, \
                          self.m, \
                          self.run_name, \
                          self.workload_type, \
                          self.host, \
                          self.port, \
                          self.cloudinitd, \
                          item.startsec, \
                          item.sleepsec, \
                          item.count, \
                          self.items]
                t = threading.Timer(item.startsec, \
                                     _submit_tasks, \
                                     t_args)
            try:
                t.start()
                self.threads.append(t)
            except Exception as e:
                self.c.log.error('Encountered problem starting Timer ' + \
                                 'thread: %s' % e)

    def _num_amqp_jobs_done(self):
        self._find_workers()
        self._fetch_logs()
        log_events = AmqpEvents(self.p, self.c, self.m, self.run_name)
        count = log_events.get_event_count('job_end')
        return count

    def _num_torque_jobs_done(self):
        self._fetch_torque_logs()
        torque_events = TorqueEvents(self.p, self.c, self.m, self.run_name)
        count = torque_events.get_event_count('job_end')
        return count

    def wait(self):
        for thread in self.threads:
            thread.join()
        if self.key == 'SUBMIT':
            jobs_running = True
            total_jobs = self._get_total_items()
            while jobs_running:
                count = 0
                if self.workload_type == 'torque':
                    count = self._num_torque_jobs_done()
                else:
                    count = self._num_amqp_jobs_done()
                self.c.log.info('Waiting for %s jobs to finish.' % total_jobs)
                self.c.log.info('Currently %s jobs have completed.' % count)
                if count >= total_jobs:
                    jobs_running=False
                if jobs_running:
                    time.sleep(60)


def _build_opts_from_dict(val):
    opts = Values()
    for key in val.keys():
        opts.__dict__[key] = val[key]
    return opts

def _kill_controller(p, c, m, run_name, startsec, cloudinitd, epucontroller):
    c.log.info("Killing controller (at evaluation second %s)" % startsec)
    # TODO: fix this hardcoded service name
    cloudinitd_terminate = get_cloudinit_for_destruction(p, c, m, run_name)
    svc = cloudinitd_terminate.get_service('epu-onesleeper')
    svc.shutdown()
    epucontroller.terminate()
    cmd = 'cloudinitd repair %s' % run_name
    c.log.debug("command = '%s'" % cmd)
    timeout = 600.0 # seconds
    (k, rc, out, err) = epumgmt.defaults.child.child(cmd, timeout=timeout)

    if k:
        c.log.error("TIMED OUT: '%s'" % cmd)

    if not rc:
        c.log.debug("command succeeded: '%s'" % cmd)
        epucontroller.start()
    else:
        errmsg = "problem running command, "
        if rc < 0:
            errmsg += "killed by signal:"
        if rc > 0:
            errmsg += "exited non-zero:"
        errmsg += "'%s' ::: return code" % cmd
        errmsg += ": %d ::: error:\n%s\noutput:\n%s" % (rc, out, err)

        # these commands will commonly fail
        if c.trace:
            self.c.log.debug(errmsg)

def _kill_vms(p, c, m, run_name, startsec, killWorkload):
    for item in killWorkload:
        if item.startsec == startsec:
            c.log.info('Killing %s VMs' % item.count)
            np = p
            np.optdict['action'] = 'fetchkill'
            np.optdict['killnum'] = str(item.count)
            nopts = _build_opts_from_dict(np.optdict)
            eopts = epumgmt.main.em_core.EPUMgmtOpts(run_name,
                                                     p.optdict['conf'],
                                                     nopts)
            epumgmt.main.em_core.core(eopts)

def _submit_tasks(p, \
                  c, \
                  m, \
                  run_name, \
                  workload_type, \
                  host, \
                  port, \
                  cloudinitd, \
                  startsec, \
                  sleepsec, \
                  count, \
                  taskWorkload):
    if workload_type == 'torque':
        jobsystem = Torque(p, c, m, run_name, cloudinitd)
    elif workload_type == 'amqp':
        jobsystem = AMQP(p, c, m, run_name, host, port)

    for item in taskWorkload:
        if (item.startsec == startsec) and \
           (item.sleepsec == sleepsec) and \
           (item.count == count):
            subStr = '%s %s %s' % (item.startsec, item.count, item.sleepsec)
            c.log.info('Submitting task: %s', subStr)
            jobsystem.submit(item)

# Execute the workload test. This assumes that the VMs have been launched
# and are in the appropriate "stable" state (i.e. they're ready for the
# test to begin).
def execute_workload_test(p, c, m, run_name):
    workloadfilename = p.get_arg_or_none('workloadfilename')
    workloadtype = p.get_arg_or_none('workloadtype').lower()

    if (workloadtype != 'torque') and (workloadtype != 'amqp'):
        c.log.error('Workload type must be torque or amqp')
        return

    c.log.info('Initializing workloads')
    epucontroller = EPUController(p, c, m, run_name)
    epucontroller.start()

    killWorkload = Workload('KILL', \
                            p, \
                            c, \
                            m, \
                            run_name, \
                            workloadfilename, \
                            workloadtype)
    taskWorkload = Workload('SUBMIT', \
                            p, \
                            c, \
                            m, \
                            run_name, \
                            workloadfilename, \
                            workloadtype)
    killControllerWorkload = Workload('KILL_CONTROLLER', \
                                      p, \
                                      c, \
                                      m, \
                                      run_name, \
                                      workloadfilename, \
                                      workloadtype, \
                                      epucontroller)

    c.log.info('Executing workloads')
    killWorkload.execute()
    taskWorkload.execute()
    killControllerWorkload.execute()

    # We deem the workload to be complete when all Timer threads have
    # finished and we observe "completed" events for all of the tasks
    # that were submitted.
    c.log.info('Waiting for the kill and task workloads to complete.')

    killControllerWorkload.wait()
    c.log.info('Kill controller workload is complete.')

    killWorkload.wait()
    c.log.info('Kill workload is complete.')

    taskWorkload.wait()
    c.log.info('Task workload is complete.')
    
