from optparse import Values
import os
import time
import json
import urllib2
import threading

from epumgmt.defaults.log_events import LogEvents
import epumgmt.api


class WorkItem:
    def __init__(self, startsec, count, sleepsec=None, batchid=0):
        self.startsec = startsec
        self.count = count
        self.sleepsec = sleepsec
        self.batchid = batchid


class Workload:
    def __init__(self, key, workloadfilename, p, c, m, run_name):
        self.items = []
        self.threads = []
        self.key = key
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name

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
        # TODO: adjust for the removal of the status command, this will fail
        actives = em_core_status.status(self.p, self.c, self.m, self.run_name)
        host = ''
        for active in actives:
            if len(active) >= 4:
                if name in active[1]:
                    host = active[3]
        return host

    def _find_workers_once(self):
        np = self.p
        np.optdict['action'] = 'find-workers-once'
        nopts = _build_opts_from_dict(np.optdict)
        eopts = epumgmt.api.EPUMgmtOpts(self.run_name, self.p.optdict['conf'], nopts)
        epumgmt.api.epumgmt_run(eopts)

    def _fetch_logs(self):
        np = self.p
        np.optdict['action'] = 'logfetch'
        nopts = _build_opts_from_dict(np.optdict)
        eopts = epumgmt.api.EPUMgmtOpts(self.run_name, self.p.optdict['conf'], nopts)
        epumgmt.api.epumgmt_run(eopts)

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
            elif self.key == 'SUBMIT':
                host = self._get_hostname('sleeper')
                t_args = [self.p, \
                          self.c, \
                          self.m, \
                          self.run_name, \
                          host, \
                          item.startsec, \
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

    def wait(self):
        for thread in self.threads:
            thread.join()
        if self.key == 'SUBMIT':
            jobs_running = True
            log_events = LogEvents(self.p, self.c, self.m, self.run_name)
            total_jobs = self._get_total_items()
            while jobs_running:
                self._find_workers_once()
                self._fetch_logs()
                count = log_events.get_event_count('job_end')
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

def _kill_vms(p, c, m, run_name, startsec, killWorkload):
    for item in killWorkload:
        if item.startsec == startsec:
            c.log.info('Killing %s VMs' % item.count)
            np = p
            np.optdict['action'] = 'fetchkill'
            np.optdict['killnum'] = str(item.count)
            nopts = _build_opts_from_dict(np.optdict)
            eopts = epumgmt.api.EPUMgmtOpts(run_name, p.optdict['conf'], nopts)
            epumgmt.api.epumgmt_run(eopts)

def _submit_tasks(p, c, m, run_name, host, startsec, taskWorkload):
    for item in taskWorkload:
        if item.startsec == startsec:
            subStr = '%s %s %s' % (item.startsec, item.count, item.sleepsec)
            c.log.info('Submitting task: %s', subStr)

            # hardcoded for now, ick -- is this in a config somewhere?
            port = '8000'

            testName = '%s-jobs' % run_name
            submitStr = 'http://%s:%s/%s/%s/%s/%s' % (host, \
                                                      port, \
                                                      testName, \
                                                      item.batchid, \
                                                      item.count, \
                                                      item.sleepsec)
            c.log.debug('submit: %s', submitStr)

            retry = 3
            while retry > 0:
                try:
                    urllib2.urlopen(submitStr, timeout=5)
                    retry = 0
                except Exception as e:
                    c.log.error('Failed to submit task at %s' % item.startsec)
                    c.log.error('Exception: %s' % e)
                    retry -= 1

# Execute the workload test. This assumes that the VMs have been launched
# and are in the appropriate "stable" state (i.e. they're ready for the
# test to begin).
def execute_workload_test(p, c, m, run_name):
    workloadfilename = p.get_arg_or_none('workloadfilename')

    c.log.info('Initializing workloads')
    killWorkload = Workload('KILL', workloadfilename, p, c, m, run_name)
    taskWorkload = Workload('SUBMIT', workloadfilename, p, c, m, run_name)

    c.log.info('Executing workloads')
    killWorkload.execute()
    taskWorkload.execute()

    # We deem the workload to be complete when all Timer threads have
    # finished and we observe "completed" events for all of the tasks
    # that were submitted.
    c.log.info('Waiting for the kill and task workloads to complete.')

    killWorkload.wait()
    c.log.info('Kill workload is complete.')

    taskWorkload.wait()
    c.log.info('Task workload is complete.')
    
