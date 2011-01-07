import datetime
import json
import os

import em_core_status

# Events: 
#  job_sent: time job sent from amqp server to worker
#  job_begin: time job starts on worker
#  fetch_killed: time VM killed
#  new_node: node launch time (earlier event)
#  node_started: node boot time (later event)
#  job_end: time job ends on worker
class LogEvents():
    def __init__(self, p, c, m, run_name):
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name

    def _create_datetime(self, timestamp):
        dateTime = datetime.datetime(timestamp['year'], \
                                     timestamp['month'], \
                                     timestamp['day'], \
                                     timestamp['hour'], \
                                     timestamp['minute'], \
                                     timestamp['second'], \
                                     timestamp['microsecond'])
        return dateTime

    # job events: job_sent
    def _set_workproducerlog_filenames(self):
        logName = 'ioncontainer.log'
        filenames = []
        baseDir = self.p.get_conf_or_none("events", "runlogdir")
        if not os.path.isabs(baseDir):
            baseDir = self.c.resolve_var_dir(baseDir)
        baseDir = os.path.join(baseDir, self.run_name)
        for root, dirs, files in os.walk(baseDir):
            if 'sleeper_work_producer' in os.path.basename(root):
                if logName in files:
                    filenames.append(os.path.join(root, logName))
        self.workproducerlog_filenames = filenames

    # node boot times and node launch times
    def _set_provisionerlog_filenames(self):
        logName = 'ioncontainer.log'
        filenames = []
        baseDir = self.p.get_conf_or_none("events", "runlogdir")
        if not os.path.isabs(baseDir):
            baseDir = self.c.resolve_var_dir(baseDir)
        baseDir = os.path.join(baseDir, self.run_name)
        for root, dirs, files in os.walk(baseDir):
            if 'provisioner' in os.path.basename(root):
                if logName in files:
                    filenames.append(os.path.join(root, logName))
        self.provisionerlog_filenames = filenames

    # job events: job_begin, job_end
    def _set_workconsumerlog_filenames(self):
        logName = 'ioncontainer.log'
        filenames = []
        baseDir = self.p.get_conf_or_none("events", "runlogdir")
        if not os.path.isabs(baseDir):
            baseDir = self.c.resolve_var_dir(baseDir)
        baseDir = os.path.join(baseDir, self.run_name)
        for root, dirs, files in os.walk(baseDir):
            if 'logs' in os.path.basename(root):
                if logName in files:
                    filenames.append(os.path.join(root, logName))
        self.workconsumerlog_filenames = filenames

    # vm fetch killed times
    def _set_vmkilllog_filenames(self):
        logName = '--' + self.run_name + '-fetchkill-'
        filenames = []
        baseDir = self.p.get_conf_or_none("logging", "logfiledir")
        if not os.path.isabs(baseDir):
            baseDir = self.c.resolve_var_dir(baseDir)
        for root, dirs, files in os.walk(baseDir):
            for fileName in files:
                if logName in fileName:
                    filenames.append(os.path.join(root, fileName))
        self.vmkilllog_filenames = filenames

    def _update_log_filenames(self):
        self.c.log.debug('Gathering log filenames')

        self.workproducerlog_filenames = None
        self.provisionerlog_filenames = None
        self.workconsumerlog_filenames = None
        self.vmkilllog_filenames = None

        self._set_workproducerlog_filenames()
        self._set_provisionerlog_filenames()
        self._set_workconsumerlog_filenames()
        self._set_vmkilllog_filenames()

    def get_event_count(self, event):
        events = self.get_event_datetimes_dict(event)
        return len(events.keys())

    def get_event_datetimes_dict(self, event):
        # first update the filenames, logs from new instances
        # may have arrived since we last ran this
        self._update_log_filenames()
        filenames = []
        jsonid = ''
        if 'fetch_killed' == event:
            filenames = self.vmkilllog_filenames
            jsonid = 'iaas_id'
        elif ('job_begin' == event) or ('job_end' == event):
            filenames = self.workconsumerlog_filenames
            jsonid = 'jobid'
        elif 'job_sent' == event:
            filenames = self.workproducerlog_filenames
            jsonid = 'jobid'
        elif 'new_node' == event:
            filenames = self.provisionerlog_filenames
            jsonid = 'iaas_id'
        elif 'node_started' == event:
            filenames = self.provisionerlog_filenames
            jsonid = 'node_id'

        eventTimes = {}
        if filenames:
            for filename in filenames:
                try:
                    eventFile = open(filename, 'r')
                    try:
                        for line in eventFile:
                            if event in line:
                                splitline = line.rpartition('JSON:')[2]
                                splitline.strip()
                                jsonEvent = json.loads(splitline)
                                timestamp = jsonEvent['timestamp']
                                eventTime = self._create_datetime(timestamp)
                                k = jsonEvent['extra'][jsonid]
                                eventTimes[k] = eventTime
                    finally:
                        eventFile.close()
                except IOError:
                    self.c.log.error('Failed to open and read from file: ' + \
                                     '%s' % filename)
        return eventTimes

