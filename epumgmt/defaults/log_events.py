import datetime
import json
from epumgmt.api.exceptions import InvalidConfig
import os

# Torque times are reported using the local timezone, e.g. pacific if using
# us-west EC2, however, EPU components are logging in UTC
UTC_OFFSET = 7

# Events:
#  EPU_CONTROLLER_START
#  EPU_CONTROLLER_TERMINATE
class ControllerEvents:
    def __init__(self, p, c, m, run_name):
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name

    def _set_controllerlog_filenames(self):
        filenames = []
        runlogdir = self.p.get_conf_or_none("events", "runlogdir")
        if not runlogdir:
            raise InvalidConfig("There is no runlogdir configuration")
        if not os.path.isabs(runlogdir):
            runlogdir = self.c.resolve_var_dir(runlogdir)
        tld = os.path.join(runlogdir, self.run_name)
        controllerlogdir = os.path.join(tld, "epucontrollerkill_logs")
        logs = os.listdir(controllerlogdir)
        for log in logs:
            filenames.append(os.path.join(controllerlogdir, log))
        self.c.log.debug("Setting controller log filenames: %s" % filenames)
        self.controllerlog_filenames = filenames

    def _update_log_filenames(self):
        self.c.log.debug('Gathering controller kill log filenames')
        self.controllerlog_filenames = None
        self._set_controllerlog_filenames()

    def get_event_count(self, event):
        events = self.get_event_datetimes_dict(event)
        return len(events.keys())

    def _create_datetime(self, date_str, time_str):
        splitdate = date_str.split('-')
        splittime = time_str.split(':')
        month = int(splitdate[1].strip())
        day = int(splitdate[2].strip())
        year = int(splitdate[0].strip())
        hour = int(splittime[0].strip())
        minute = int(splittime[1].strip())
        second = int(splittime[2].strip().split('.')[0].strip())
        microsecond = int(splittime[2].strip().split('.')[1].strip())
        dateTime = datetime.datetime(year, \
                                     month, \
                                     day, \
                                     hour, \
                                     minute, \
                                     second, \
                                     microsecond)
        return dateTime

    def get_event_datetimes_list(self, orig_event):
        self._update_log_filenames()
        # all of these events will be in the server_log files
        filenames = self.controllerlog_filenames
        event = orig_event

        event_times = []
        if filenames:
            for filename in filenames:
                try:
                    event_file = open(filename, 'r')
                    try:
                        for line in event_file:
                            if event in line:
                                splitline = line.split()
                                lineevent = splitline[0]
                                date_str = splitline[1].strip()
                                time_str = splitline[2].strip()
                                event_time = self._create_datetime(date_str, time_str)
                                event_times.append(event_time)
                    finally:
                        event_file.close()
                except IOError:
                    self.c.log.error('Failed to open and read from file: ' + \
                                     '%s' % filename)
        return event_times

# Events:
#  job_sent: Job Queued
#  job_begin: Job Run
#  job_end: Exit_status
class TorqueEvents:
    def __init__(self, p, c, m, run_name):
        self.p = p
        self.c = c
        self.m = m
        self.run_name = run_name

    def _set_serverlog_filenames(self):
        filenames = []
        runlogdir = self.p.get_conf_or_none("events", "runlogdir")
        if not runlogdir:
            raise InvalidConfig("There is no runlogdir configuration")
        if not os.path.isabs(runlogdir):
            runlogdir = self.c.resolve_var_dir(runlogdir)
        tld = os.path.join(runlogdir, self.run_name)
        torquelogdir = os.path.join(tld, "torque-server_logs")
        logs = os.listdir(torquelogdir)
        for log in logs:
            filenames.append(os.path.join(torquelogdir, log))
        self.c.log.debug("Setting server log filenames: %s" % filenames)
        self.serverlog_filenames = filenames

    def _update_log_filenames(self):
        self.c.log.debug('Gathering torque log filenames')
        self.serverlog_filenames = None
        self._set_serverlog_filenames()

    def get_event_count(self, event):
        events = self.get_event_datetimes_dict(event)
        return len(events.keys())

    def _create_datetime(self, date_str, time_str):
        splitdate = date_str.split('/')
        splittime = time_str.split(':')
        month = int(splitdate[0].strip())
        day = int(splitdate[1].strip())
        year = int(splitdate[2].strip())
        hour = int(splittime[0].strip()) + UTC_OFFSET
        minute = int(splittime[1].strip())
        second = int(splittime[2].strip())
        microsecond = 0
        dateTime = datetime.datetime(year, \
                                     month, \
                                     day, \
                                     hour, \
                                     minute, \
                                     second, \
                                     microsecond)
        return dateTime

    def get_event_datetimes_dict(self, orig_event):
        self._update_log_filenames()
        # all of these events will be in the server_log files
        filenames = self.serverlog_filenames
        event = orig_event
        if orig_event == 'job_sent':
            event = 'Job Queued'
        elif orig_event == 'job_begin':
            event = 'Job Run'
        elif orig_event == 'job_end':
            event = 'Exit_status'
        else:
            self.c.log.error("Unrecognized event: %s" % event)
            return {}

        event_times = {}
        if filenames:
            for filename in filenames:
                try:
                    event_file = open(filename, 'r')
                    try:
                        for line in event_file:
                            if event in line:
                                splitline = line.split()
                                splitinfo = splitline[1].split(';')
                                date_str = splitline[0].strip()
                                time_str = splitinfo[0].strip()
                                event_time = self._create_datetime(date_str, time_str)
                                job_id = int(splitinfo[4].strip().split('.')[0].strip())
                                print splitinfo
                                event_times[job_id] = event_time
                    finally:
                        event_file.close()
                except IOError:
                    self.c.log.error('Failed to open and read from file: ' + \
                                     '%s' % filename)
        self.c.log.debug("Event %s times: %s" % (orig_event, event_times))
        return event_times

# Events:
#  fetch_killed: time VM killed
#  new_node: node launch time (earlier event)
#  node_started: node boot time (later event)
class NodeEvents:
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

    # vm fetch killed times
    def _set_vmkilllog_filenames(self):
        logName = '--' + self.run_name + '-fetchkill-'
        filenames = []
        baseDir = self.p.get_conf_or_none("logging", "logfiledir")
        if not os.path.isabs(baseDir):
            baseDir = self.c.resolve_var_dir(baseDir)
        for root, dirs, files in os.walk(baseDir):
            print files
            for fileName in files:
                if logName in fileName:
                    filenames.append(os.path.join(root, fileName))
        self.vmkilllog_filenames = filenames

    def _update_log_filenames(self):
        self.c.log.debug('Gathering node log filenames')

        self.provisionerlog_filenames = None
        self.vmkilllog_filenames = None

        self._set_provisionerlog_filenames()
        self._set_vmkilllog_filenames()

    def get_event_count(self, event):
        events = self.get_event_datetimes_dict(event)
        return len(events.keys())

    def get_event_datetimes_dict(self, event):
        # first update the filenames, logs from new instances
        # may have arrived since we last ran this
        self._update_log_filenames()
        filenames = []

        if 'launch_ctx_done' == event:
            jsonid = 'node_ids'
        else:
            jsonid = ''

        if 'fetch_killed' == event:
            filenames = self.vmkilllog_filenames
        elif 'new_node' == event:
            filenames = self.provisionerlog_filenames
        elif 'terminated_node' == event:
            filenames = self.provisionerlog_filenames
        elif 'node_started' == event:
            filenames = self.provisionerlog_filenames
        elif 'launch_ctx_done' == event:
            filenames = self.provisionerlog_filenames
        else:
            self.c.log.error("Unrecognized event: %s" % event)
            return {}

        event_times = {}
        if filenames:
            for filename in filenames:
                try:
                    event_file = open(filename, 'r')
                    try:
                        for line in event_file:
                            if event in line:
                                if not jsonid:
                                    if 'iaas_id' in line:
                                        jsonid = 'iaas_id'
                                    else:
                                        jsonid = 'node_id'
                                splitline = line.rpartition('JSON:')[2]
                                splitline.strip()
                                try:
                                    jsonEvent = json.loads(splitline)
                                except:
                                    emsg = "Problem parsing JSON: '%s'"
                                    self.c.log.exception(emsg % splitline)
                                    continue
                                timestamp = jsonEvent['timestamp']
                                event_time = self._create_datetime(timestamp)
                                if event == 'launch_ctx_done':
                                    k = jsonEvent['extra'][jsonid][0]
                                else:
                                    k = jsonEvent['extra'][jsonid]
                                event_times[k] = event_time
                    finally:
                        event_file.close()
                except IOError:
                    self.c.log.error('Failed to open and read from file: ' + \
                                     '%s' % filename)
        return event_times

# Events:
#  job_sent: time job sent from amqp server to worker
#  job_begin: time job starts on worker
#  job_end: time job ends on worker
class AmqpEvents:
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
            if 'producer1-container' in os.path.basename(root):
                if logName in files:
                    filenames.append(os.path.join(root, logName))
        self.workproducerlog_filenames = filenames

    # job events: job_begin, job_end
    def _set_workconsumerlog_filenames(self):
        logName = 'ioncontainer.log'
        filenames = []
        baseDir = self.p.get_conf_or_none("events", "runlogdir")
        if not os.path.isabs(baseDir):
            baseDir = self.c.resolve_var_dir(baseDir)
        baseDir = os.path.join(baseDir, self.run_name)
        for root, dirs, files in os.walk(baseDir):
            if 'epuworker_container' in os.path.basename(root):
                if logName in files:
                    filenames.append(os.path.join(root, logName))
        self.workconsumerlog_filenames = filenames

    def _update_log_filenames(self):
        self.c.log.debug('Gathering amqp log filenames')

        self.workproducerlog_filenames = None
        self.workconsumerlog_filenames = None

        self._set_workproducerlog_filenames()
        self._set_workconsumerlog_filenames()

    def get_event_count(self, event):
        events = self.get_event_datetimes_dict(event)
        return len(events.keys())

    def get_event_datetimes_dict(self, event):
        # first update the filenames, logs from new instances
        # may have arrived since we last ran this
        self._update_log_filenames()
        filenames = []
        jsonid = ''
        if ('job_begin' == event) or ('job_end' == event):
            filenames = self.workconsumerlog_filenames
            jsonid = 'jobid'
        elif 'job_sent' == event:
            filenames = self.workproducerlog_filenames
            jsonid = 'jobid'
        else:
            self.c.log.error("Unrecognized event: %s" % event)
            return {}

        event_times = {}
        if filenames:
            for filename in filenames:
                try:
                    event_file = open(filename, 'r')
                    try:
                        for line in event_file:
                            if event in line:
                                splitline = line.rpartition('JSON:')[2]
                                splitline.strip()
                                jsonEvent = json.loads(splitline)
                                timestamp = jsonEvent['timestamp']
                                event_time = self._create_datetime(timestamp)
                                k = jsonEvent['extra'][jsonid]
                                event_times[k] = event_time
                    finally:
                        event_file.close()
                except IOError:
                    self.c.log.error('Failed to open and read from file: ' + \
                                     '%s' % filename)
        return event_times

