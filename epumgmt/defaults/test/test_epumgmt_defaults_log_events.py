import os
import shutil
import tempfile
import ConfigParser

import epumgmt.defaults.log_events
from epumgmt.defaults import DefaultParameters
from epumgmt.mocks.common import FakeCommon

class TestAmqpEvents:

    def setup(self):

        self.runlogdir = tempfile.mkdtemp()
        self.vmlogdir = tempfile.mkdtemp()

        producer_dir = os.path.join(self.runlogdir, "producer1-container")
        os.mkdir(producer_dir)
        self.producer_ioncontainer_log = os.path.join(producer_dir, "ioncontainer.log")
        with open(self.producer_ioncontainer_log, "w") as container_file:
            container_file.write("contents!")

        consumer_dir = os.path.join(self.runlogdir, "epuworker_container")
        os.mkdir(consumer_dir)
        self.consumer_ioncontainer_log = os.path.join(consumer_dir, "ioncontainer.log")
        with open(self.consumer_ioncontainer_log, "w") as container_file:
            container_file.write("contents!")

        self.config = ConfigParser.RawConfigParser()
        self.config.add_section("events")
        self.config.set("events", "runlogdir", self.runlogdir)
        self.config.set("events", "vmlogdir", self.vmlogdir)

        
        self.c = FakeCommon()
        self.p = DefaultParameters(self.config, None)
        self.amqp_events = epumgmt.defaults.log_events.AmqpEvents(self.p, self.c, None, "")

    def teardown(self):

        shutil.rmtree(self.runlogdir)
        shutil.rmtree(self.vmlogdir)

    def test_create_datetime(self):

        year = 2011
        month = 4
        day = 5
        hour = 4
        minute = 3
        second = 7
        microsecond = 6
        timestamp = { "year": year, "month": month, "day": day,
                      "hour": hour, "minute": minute, "second": second,
                      "microsecond": microsecond }
        
        got_datetime = self.amqp_events._create_datetime(timestamp)

        print dir(got_datetime)

        assert got_datetime.year == year
        assert got_datetime.minute == minute
        assert got_datetime.day == day


    def test_set_workproducerlog_filenames(self):

        self.amqp_events._set_workproducerlog_filenames()
        assert self.producer_ioncontainer_log in self.amqp_events.workproducerlog_filenames

    
    def test_set_workconsumerlog_filenames(self):

        self.amqp_events._set_workconsumerlog_filenames()
        assert self.consumer_ioncontainer_log in self.amqp_events.workconsumerlog_filenames


    def test_update_log_filenames(self):

        self.amqp_events._update_log_filenames()
        assert self.consumer_ioncontainer_log in self.amqp_events.workconsumerlog_filenames
        assert self.producer_ioncontainer_log in self.amqp_events.workproducerlog_filenames


    def test_get_event_datetimes_dict(self):

        got_datetimes = self.amqp_events.get_event_datetimes_dict("fake event")
        assert got_datetimes == {}


        job_begin_id = 545454
        job_begin_event = '2011-07-07 11:03:07,532 [cei_events     : 32] WARNING:CLOUDYVENT_JSON: {"eventname": "job_begin", "timestamp": {"hour": 18, "month": 7, "second": 7, "microsecond": 532627, "year": 2011, "day": 7, "minute": 4}, "uniquekey": "2c5a9f30-a1b8-4621-ac68-d66ca1cd99f5", "eventsource": "worker", "extra": {"batchid": "xchg1310061055-jobs", "work_amount": 0, "jobid": %s}}\n' % job_begin_id
        job_end_id = 424242
        job_end_event = '2011-07-07 11:04:07,532 [cei_events     : 32] WARNING:CLOUDYVENT_JSON: {"eventname": "job_end", "timestamp": {"hour": 18, "month": 7, "second": 7, "microsecond": 532627, "year": 2011, "day": 7, "minute": 4}, "uniquekey": "2c5a9f30-a1b8-4621-ac68-d66ca1cd99f5", "eventsource": "worker", "extra": {"batchid": "xchg1310061055-jobs", "work_amount": 0, "jobid": %s}}\n' % job_end_id
        
        with open(self.consumer_ioncontainer_log, "w") as container:
            container.write(job_begin_event + job_end_event)

        job_sent_id = 424244
        job_sent_event = '2011-07-07 11:04:07,532 [cei_events     : 32] WARNING:CLOUDYVENT_JSON: {"eventname": "job_sent", "timestamp": {"hour": 18, "month": 7, "second": 7, "microsecond": 532627, "year": 2011, "day": 7, "minute": 4}, "uniquekey": "2c5a9f30-a1b8-4621-ac68-d66ca1cd99f5", "eventsource": "worker", "extra": {"batchid": "xchg1310061055-jobs", "work_amount": 0, "jobid": %s}}\n' % job_sent_id

        with open(self.producer_ioncontainer_log, "w") as container:
            container.write(job_sent_event)


        got_datetimes = self.amqp_events.get_event_datetimes_dict("job_end")
        assert got_datetimes.has_key(job_end_id)

        
        got_datetimes = self.amqp_events.get_event_datetimes_dict("job_begin")
        assert got_datetimes.has_key(job_begin_id)

        
        got_datetimes = self.amqp_events.get_event_datetimes_dict("job_sent")
        assert got_datetimes.has_key(job_sent_id)

    def test_get_event_datetimes_dict_badfile(self):

        job_sent_id = 424244
        job_sent_event = '2011-07-07 11:04:07,532 [cei_events     : 32] WARNING:CLOUDYVENT_JSON: {"eventname": "job_sent", "timestamp": {"hour": 18, "month": 7, "second": 7, "microsecond": 532627, "year": 2011, "day": 7, "minute": 4}, "uniquekey": "2c5a9f30-a1b8-4621-ac68-d66ca1cd99f5", "eventsource": "worker", "extra": {"batchid": "xchg1310061055-jobs", "work_amount": 0, "jobid": %s}}\n' % job_sent_id

        with open(self.producer_ioncontainer_log, "w") as container:
            container.write(job_sent_event)

        old_mode = os.stat(self.producer_ioncontainer_log).st_mode
        os.chmod(self.producer_ioncontainer_log, 0)
        got_datetimes = self.amqp_events.get_event_datetimes_dict("job_sent")

        failed_to_open = [message for (level, message)
            in self.c.log.transcript 
            if level == "ERROR"
            and "Failed to open and read" in message]

        assert len(failed_to_open) == 1
        os.chmod(self.producer_ioncontainer_log, old_mode)

    def test_get_event_count(self):

        job_sent_id = 424244
        job_sent_event = '2011-07-07 11:04:07,532 [cei_events     : 32] WARNING:CLOUDYVENT_JSON: {"eventname": "job_sent", "timestamp": {"hour": 18, "month": 7, "second": 7, "microsecond": 532627, "year": 2011, "day": 7, "minute": 4}, "uniquekey": "2c5a9f30-a1b8-4621-ac68-d66ca1cd99f5", "eventsource": "worker", "extra": {"batchid": "xchg1310061055-jobs", "work_amount": 0, "jobid": %s}}\n' % job_sent_id

        with open(self.producer_ioncontainer_log, "w") as container:
            container.write(job_sent_event)

        count = self.amqp_events.get_event_count("job_sent")
        assert count == 1


class TestControllerEvents:

    def setup(self):
        self.vardir = tempfile.mkdtemp()
        self.runlogdir = "runlogs"
        self.vmlogdir = "vmlogs"

        self.test_event = "testevent 4-5-6 12:12:12.12"

        controller_dir = os.path.join(self.vardir, self.runlogdir, "epucontrollerkill_logs")
        os.makedirs(controller_dir)
        self.controller_ioncontainer_log = os.path.join(controller_dir, "ioncontainer.log")
        with open(self.controller_ioncontainer_log, "w") as container_file:
            container_file.write(self.test_event)

        self.config = ConfigParser.RawConfigParser()
        self.config.add_section("events")
        self.config.set("events", "runlogdir", self.runlogdir)
        self.config.add_section("ecdirs")
        self.config.set("ecdirs", "var", self.vardir)

        
        self.p = DefaultParameters(self.config, None)
        self.c = FakeCommon(self.p)
        self.controller_events = epumgmt.defaults.log_events.ControllerEvents(self.p, self.c, None, "")


    def teardown(self):

        shutil.rmtree(self.vardir)

    def test_set_controllerlog_filenames(self):

        self.controller_events._set_controllerlog_filenames()

        assert self.controller_ioncontainer_log in self.controller_events.controllerlog_filenames

    def test_update_log_filenames(self):

        self.controller_events._update_log_filenames()
        assert self.controller_ioncontainer_log in self.controller_events.controllerlog_filenames

    def test_create_datetime(self):

        month = 8
        day = 9
        year = 1985
        hour = 1
        minute = 42
        second = 43
        microsecond = 44
        date_string = "%s - %s - %s" % (year, month, day)
        time_string = "%s:%s:%s.%s" % (hour, minute, second, microsecond)

        datetime = self.controller_events._create_datetime(date_string, time_string)

        assert datetime.month == month

        
    def test_get_event_datetimes_list(self):

        event = "testevent"
        event_list = self.controller_events.get_event_datetimes_list(event)
        assert len(event_list) == 1


class TestTorqueEvents:

    def setup(self):
        self.vardir = tempfile.mkdtemp()
        self.runlogdir = "runlogs"
        self.vmlogdir = "vmlogs"
        self.job_id = 5
        self.torque_event = "05/25/2011 15:57:42;0008;PBS_Server;Job;%s.ip-10-203-66-146.ec2.internal;Job Queued at request of ubuntu@ip-10-203-66-146.ec2.internal, owner = ubuntu@ip-10-203-66-146.ec2.internal, job name = tmp5TEZaU, queue = default" % self.job_id
        torque_dir = os.path.join(self.vardir, self.runlogdir, "torque-server_logs")
        os.makedirs(torque_dir)
        self.torque_log = os.path.join(torque_dir, "torque.log")
        with open(self.torque_log, "w") as torque_file:
            torque_file.write(self.torque_event)

        self.config = ConfigParser.RawConfigParser()
        self.config.add_section("events")
        self.config.set("events", "runlogdir", self.runlogdir)
        self.config.add_section("ecdirs")
        self.config.set("ecdirs", "var", self.vardir)

        
        self.p = DefaultParameters(self.config, None)
        self.c = FakeCommon(self.p)
        self.torque_events = epumgmt.defaults.log_events.TorqueEvents(self.p, self.c, None, "")


    def test_set_serverlog_filenames(self):

        self.torque_events._set_serverlog_filenames()
        assert self.torque_log in self.torque_events.serverlog_filenames

    def test_update_log_filenames(self):

        self.torque_events._update_log_filenames()
        assert self.torque_log in self.torque_events.serverlog_filenames

    def test_create_datetime(self):

        year = 2011
        month = 4
        day = 5
        hour = 4
        minute = 3
        second = 7
        microsecond = 6
        date = "%s/%s/%s" % (month, day, year)
        time = "%s:%s:%s" % (hour, minute, second)
        
        got_datetime = self.torque_events._create_datetime(date, time)

        print dir(got_datetime)

        assert got_datetime.year == year
        assert got_datetime.minute == minute
        assert got_datetime.day == day
        assert got_datetime.hour - epumgmt.defaults.log_events.UTC_OFFSET == hour


    def test_get_event_datetimes_dict(self):

        # Test behaviour with bad event type
        event = "non-existent"
        event_times = self.torque_events.get_event_datetimes_dict(event)
        assert event_times == {}

        # Test correct parsing behaviour
        event = "job_sent"
        event_times = self.torque_events.get_event_datetimes_dict(event)
        assert event_times.has_key(self.job_id)

        # Test handling of non-readable file
        self.c.log.transcript = []
        os.chmod(self.torque_log, 0)
        event = "job_sent"
        event_times = self.torque_events.get_event_datetimes_dict(event)
        errors = [message for (level, message)
                  in self.c.log.transcript
                    if level == "ERROR"]
        print errors
        assert "Failed to open and read from file" in errors[0]

class TestNodeEvents:

    def setup(self):
        self.vardir = tempfile.mkdtemp()
        self.runlogdir = "runlogs"
        self.logfiledir = "logs"
        self.run_name = "test-run"
        self.launch_ctx_id = "imauuidhonest"
        self.launch_ctx_done = "2011-06-14 09:33:08,268 [cei_events     : 32] WARNING:CLOUDYVENT_JSON: {\"eventname\": \"launch_ctx_done\", \"timestamp\": {\"hour\": 16, \"month\": 6, \"second\": 8, \"microsecond\": 268628, \"year\": 2011, \"day\": 14, \"minute\": 33}, \"uniquekey\": \"8311960b-2802-4976-ae4d-1c4e7e7b9ee5\", \"eventsource\": \"provisioner\", \"extra\": {\"launch_id\": \"e62df223-0d7d-4882-8583-98de1c14f5c8\", \"node_ids\": [\"%s\"]}}" % self.launch_ctx_id
        self.vmkill_event_id = "arealid"
        self.vmkill_event = "2011-06-14 09:33:08,268 [cei_events     : 32] WARNING:CLOUDYVENT_JSON: {\"eventname\": \"fetch_killed\", \"timestamp\": {\"hour\": 16, \"month\": 6, \"second\": 8, \"microsecond\": 268628, \"year\": 2011, \"day\": 14, \"minute\": 33}, \"uniquekey\": \"8311960b-2802-4976-ae4d-1c4e7e7b9ee5\", \"eventsource\": \"provisioner\", \"extra\": {\"launch_id\": \"e62df223-0d7d-4882-8583-98de1c14f5c8\", \"iaas_id\": \"%s\"}}" % self.vmkill_event_id
        provisioner_dir = os.path.join(self.vardir, self.runlogdir, self.run_name, "provisioner")
        os.makedirs(provisioner_dir)
        vmkill_dir = os.path.join(self.vardir, self.logfiledir)
        os.makedirs(vmkill_dir)
        self.provisioner_log = os.path.join(provisioner_dir, "ioncontainer.log")
        with open(self.provisioner_log, "w") as provisioner_file:
            provisioner_file.write(self.launch_ctx_done)
        self.vmkill_log = os.path.join(vmkill_dir, "--%s-fetchkill-" % self.run_name)
        with open(self.vmkill_log, "w") as vmkill_file:
            vmkill_file.write(self.vmkill_event)

        self.config = ConfigParser.RawConfigParser()
        self.config.add_section("events")
        self.config.set("events", "runlogdir", self.runlogdir)
        self.config.add_section("logging")
        self.config.set("logging", "logfiledir", self.logfiledir)
        self.config.add_section("ecdirs")
        self.config.set("ecdirs", "var", self.vardir)

        
        self.p = DefaultParameters(self.config, None)
        self.c = FakeCommon(self.p)
        self.node_events = epumgmt.defaults.log_events.NodeEvents(self.p, self.c, None, self.run_name)

    def teardown(self):
        shutil.rmtree(self.vardir)

    def test_create_datetime(self):

        year = 2011
        month = 4
        day = 5
        hour = 4
        minute = 3
        second = 7
        microsecond = 6
        timestamp = { "year": year, "month": month, "day": day,
                      "hour": hour, "minute": minute, "second": second,
                      "microsecond": microsecond }
        
        got_datetime = self.node_events._create_datetime(timestamp)

        print dir(got_datetime)

        assert got_datetime.year == year
        assert got_datetime.minute == minute
        assert got_datetime.day == day

    def test_set_provisionerlog_filenames(self):

        self.node_events._set_provisionerlog_filenames()
        assert self.provisioner_log in self.node_events.provisionerlog_filenames

    def test_set_vmkilllog_filenames(self):

        self.node_events._set_vmkilllog_filenames()
        assert self.vmkill_log in self.node_events.vmkilllog_filenames

    def test_update_log_filenames(self):

        self.node_events._update_log_filenames()
        assert self.vmkill_log in self.node_events.vmkilllog_filenames
        assert self.provisioner_log in self.node_events.provisionerlog_filenames

    
    def test_get_event_datetimes_dict(self):

        event = "fake-event"
        event_times = self.node_events.get_event_datetimes_dict(event)
        assert event_times == {}

        event = "launch_ctx_done"
        event_times = self.node_events.get_event_datetimes_dict(event)
        print event_times
        assert event_times.has_key(self.launch_ctx_id)

        event = "fetch_killed"
        event_times = self.node_events.get_event_datetimes_dict(event)
        print event_times
        assert event_times.has_key(self.vmkill_event_id)


        # test when we have an unreadable file
        self.c.log.transcript = []
        os.chmod(self.provisioner_log, 0)
        event = "launch_ctx_done"
        event_times = self.node_events.get_event_datetimes_dict(event)
        print event_times
        failed_to_open = [message for (level, message)
            in self.c.log.transcript 
            if level == "ERROR"
            and "Failed to open and read" in message]

        assert len(failed_to_open) == 1



    def test_get_event_count(self):

        event_count = self.node_events.get_event_count("launch_ctx_done")
        print event_count
        assert event_count == 1

