import os
import shutil
import tempfile
import ConfigParser

import epumgmt.defaults.log_events
from epumgmt.defaults import DefaultParameters
from mocks.common import FakeCommon

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
