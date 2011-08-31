from pylab import *

import matplotlib
import json
import os

from epumgmt.api.exceptions import *
from epumgmt.defaults.log_events import AmqpEvents, TorqueEvents, NodeEvents, ControllerEvents

props = matplotlib.font_manager.FontProperties(size=10)

def validate(p):
    """Validate input for our graph type

       raises InvalidInput on bad input
    """

    graphname = p.get_arg_or_none('graphname')
    if not graphname:
        raise InvalidInput("You must specify a --graphname for the 'generate-graph' action")

    graphtype = p.get_arg_or_none('graphtype')
    if not graphtype:
        raise InvalidInput("You must specify a --graphtype for the 'generate-graph' action")

    workloadtype = p.get_arg_or_none('workloadtype')
    if not workloadtype:
        raise InvalidInput("You must specify a --workloadtype for the 'generate-graph' action")



def _convert_datetime_to_seconds(dateTime):
    seconds = (dateTime.microseconds +
               (dateTime.seconds + dateTime.days * 24 * 3600)
               * 10**6) / 10**6
    return seconds

def _get_datetime_diff_seconds(begin, end):
    diff = end - begin
    seconds = _convert_datetime_to_seconds(diff)
    return seconds

def _get_first_datetime(datetimes):
    if {} == datetimes:
        return
    firsttime = datetimes[datetimes.keys()[0]]
    for key in datetimes.keys():
        if not key:
            continue
        if datetimes[key] < firsttime:
            firsttime = datetimes[key]
    return firsttime

def _get_last_datetime(datetimes):
    if {} == datetimes:
        return
    endtime = datetimes[datetimes.keys()[0]]
    for key in datetimes.keys():
        if datetimes[key] > endtime:
            endtime = datetimes[key]
    return endtime

def _get_eval_seconds_list(begin, end):
    total_seconds = _get_datetime_diff_seconds(begin, end) + 60
    return range(total_seconds)

def _get_eval_begin_datetime(*args):
    if len(args) <= 0:
        return

    firsttime = None
    for arg in args:
        if not arg:
            continue
        firsttime = _get_first_datetime(arg)
        break
    for arg in args:
        if not arg:
            continue
        for key in arg.keys():
            if firsttime > arg[key]:
                firsttime = arg[key]
    return firsttime
            
def _get_eval_end_datetime(*args):
    if len(args) <= 0:
        return

    lasttime = None
    for arg in args:
        if not arg:
            continue
        lasttime = _get_last_datetime(arg)

    if not lasttime:
        return None

    for arg in args:
        for key in arg.keys():
            if lasttime < arg[key]:
                lasttime = arg[key]
    return lasttime

def _get_unique_graph_filename(key, run_name, filetype):
    basedir = os.path.abspath('.')
    filenum = 0
    filename = os.path.join(basedir,
                            run_name + '-' +
                            key + '-' +
                            str(filenum) + '.' +
                            filetype)
    while os.path.exists(filename):
        filenum += 1
        filename = os.path.join(basedir,
                                run_name + '-' +
                                key + '-' +
                                str(filenum) + '.' +
                                filetype)
    return filename

def _get_killed_vms_list(log_events, seconds, begin, killed_datetimes):
    killedvms = {}
    for second in seconds:
        killedvms[second] = 0

    for key in killed_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, killed_datetimes[key])
        try:
            killedvms[diff] += 1
        except:
            log_events.c.log.error('problem adding to killedvms: %s' % diff)

    returnlist = []
    keys = killedvms.keys()
    keys.sort()
    for key in keys:
        returnlist.append(killedvms[key])
    return returnlist

def _get_reconfigured_list(log_events,
                           seconds,
                           begin,
                           reconfigure_datetimes):
    
    reconfigure_events = {}
    for second in seconds:
        reconfigure_events[second] = 0

    max_seconds = max(seconds)

    for key in reconfigure_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, reconfigure_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                reconfigure_events[second] += 1
                second += 1
        else:
            log_events.c.log.error('running vm time does not appear to be ' + \
                                   'valid: %s' % diff)

    returnlist = []
    keys = reconfigure_events.keys()
    keys.sort()
    for key in keys:
        returnlist.append(reconfigure_events[key])
    return returnlist

def _get_running_vms_list(log_events,
                          seconds,
                          begin,
                          start_datetimes,
                          killed_datetimes):
    runningvms = {}
    for second in seconds:
        runningvms[second] = 0

    max_seconds = max(seconds)

    for key in start_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, start_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                runningvms[second] += 1
                second += 1
        else:
            log_events.c.log.error('running vm time does not appear to be ' + \
                                   'valid: %s' % diff)
    for key in killed_datetimes.keys(): 
        diff = _get_datetime_diff_seconds(begin, killed_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                runningvms[second] -= 1
                second += 1
        else:
            log_events.c.log.error('killed vm time does not appear to be ' + \
                                   'valid: %s' % diff)

    returnlist = []
    keys = runningvms.keys()
    keys.sort()
    for key in keys:
        returnlist.append(runningvms[key])
    return returnlist

def _get_jobs_running_list(log_events,
                           seconds,
                           begin,
                           job_begin_datetimes,
                           job_end_datetimes):
    jobs = {}
    for second in seconds:
        jobs[second] = 0

    max_seconds = max(seconds)

    for key in job_begin_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_begin_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                jobs[second] += 1
                second += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    for key in job_end_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_end_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                jobs[second] -= 1
                second += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    returnlist = []
    keys = jobs.keys()
    keys.sort()
    for key in keys:
        returnlist.append(jobs[key])
    return returnlist

def _get_jobs_completed_rate_list(log_events,
                                  seconds,
                                  begin,
                                  job_end_datetimes):
    jobs = {}
    for second in seconds:
        jobs[second] = 0

    max_seconds = max(seconds)

    for key in job_end_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_end_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            jobs[second] += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    returnlist = []
    keys = jobs.keys()
    keys.sort()
    for key in keys:
        returnlist.append(jobs[key])
    return returnlist

def _get_jobs_queued_list(log_events,
                          seconds,
                          begin,
                          job_sent_datetimes,
                          job_begin_datetimes):
    jobs = {}
    for second in seconds:
        jobs[second] = 0

    max_seconds = max(seconds)

    for key in job_sent_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_sent_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                jobs[second] += 1
                second += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    for key in job_begin_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_begin_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                jobs[second] -= 1
                second += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    returnlist = []
    keys = jobs.keys()
    keys.sort()
    for key in keys:
        returnlist.append(jobs[key])
    return returnlist

def _get_jobs_list(log_events, seconds, begin, job_datetimes):
    jobs = {}
    for second in seconds:
        jobs[second] = 0

    max_seconds = max(seconds)

    for key in job_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_datetimes[key])
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                jobs[second] += 1
                second += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    returnlist = []
    keys = jobs.keys()
    keys.sort()
    for key in keys:
        returnlist.append(jobs[key])
    return returnlist

def _get_jobtts_list(log_events, job_begin_datetimes, job_sent_datetimes):
    jobtts = {}
    for key in job_sent_datetimes.keys():
        jobtts[key] = 0

    for key in job_sent_datetimes.keys():
        try:
            job_sent = job_sent_datetimes[key]
            job_begin = job_begin_datetimes[key]
            jobtts[key] = _get_datetime_diff_seconds(job_sent, job_begin)
        except:
            jobtts[key] = 0

    returnlist = []
    keys = jobtts.keys()
    keys.sort()
    for key in keys:
        returnlist.append(jobtts[key])
    return returnlist

def _get_killed_controller_list(seconds, begin, killed_datetimes):
    vms = {}
    for second in seconds:
        vms[second] = 0

    max_seconds = max(seconds)

    for event_time in killed_datetimes: 
        diff = _get_datetime_diff_seconds(begin, event_time)
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            vms[second] += 1

    returnlist = []
    keys = vms.keys()
    keys.sort()
    for key in keys:
        returnlist.append(vms[key])
    return returnlist

def _get_nodeinfo_list(events, ids, ctxdone_datetimes, nodestarted_datetimes, first):
    ctxdone = []
    nodestarted = []
    new_ids = []
    for anid in ids:
        try:
            ctx_diff =  _get_datetime_diff_seconds(first[anid], ctxdone_datetimes[anid])
            start_diff = _get_datetime_diff_seconds(first[anid], nodestarted_datetimes[anid])
            ctxdone.append(ctx_diff)
            nodestarted.append(start_diff)
            new_ids.append(anid)
        except KeyError:
            events.c.log.warn("skipping node: %s" % anid)
    return new_ids, ctxdone, nodestarted

def _get_running_controller_list(seconds, begin, running_datetimes, killed_datetimes):
    vms = {}
    for second in seconds:
        vms[second] = 0

    max_seconds = max(seconds)

    for event_time in running_datetimes:
        diff = _get_datetime_diff_seconds(begin, event_time)
        if diff < 0:
            diff = 0
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                vms[second] += 1
                second += 1

    for event_time in killed_datetimes: 
        diff = _get_datetime_diff_seconds(begin, event_time)
        if (diff >= 0) and (diff <= max_seconds):
            second = diff
            while second <= max_seconds:
                vms[second] -= 1
                second += 1

    returnlist = []
    keys = vms.keys()
    keys.sort()
    for key in keys:
        returnlist.append(vms[key])
    return returnlist

# added for very large job_end workloads...
def _get_job_rate_from_file(log_events, node_events, begin, seconds):
    log_events._set_workproducerlog_filenames()
    filenames = log_events.workconsumerlog_filenames
    jobs = {}
    for second in seconds:
        jobs[second] = 0

    max_seconds = max(seconds)

    event = 'job_end'
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
                            eventTime = log_events._create_datetime(timestamp)
                            diff = _get_datetime_diff_seconds(begin, eventTime)
                            if (diff >= 0) and (diff <= max_seconds):
                                second = diff
                                jobs[second] += 1
                            else:
                                log_events.c.log.error('job time does not appear to be ' + \
                                                       'valid: %s' % diff)

                finally:
                    eventFile.close()
            except IOError:
                self.c.log.error('Failed to open and read from file: ' + \
                                 '%s' % filename)

    returnlist = []
    keys = jobs.keys()
    keys.sort()
    for key in keys:
        returnlist.append(jobs[key])
    return returnlist

def _generate_job_tts(log_events, node_events, run_name, graphtype='eps'):
    filename = _get_unique_graph_filename('job-tts', run_name, graphtype)

    job_sent_datetimes = log_events.get_event_datetimes_dict('job_sent')
    job_begin_datetimes = log_events.get_event_datetimes_dict('job_begin')

    jobids = job_sent_datetimes.keys()
    jobids.sort()

    jobtts_list = _get_jobtts_list(log_events,
                                   job_begin_datetimes,
                                   job_sent_datetimes)

    # graph
    xmin = min(jobids)
    xmax = max(jobids)
    ymin = min(jobtts_list)
    ymax = max(jobtts_list)

    fig = figure()

    clf()

    fig.suptitle('Job Time to Start',
                 verticalalignment='top',
                 horizontalalignment='center')

    # bottom graph
    ax = fig.add_subplot(1,1,1)
    ax.set_ylabel('Seconds')
    ax.set_xlabel('Job ID')
    ax.axis([xmin, xmax, ymin, ymax])
    if len(jobids) <= 20:
        xticks(jobids)
    ylim(0, ymax)
    if len(jobids) < 100:
        h1 = ax.stem(jobids, jobtts_list, '-')
        setp(h1[0], 'markerfacecolor', 'b')
        for line in h1[1]:
            setp(line, 'color', 'b')
        ax.legend([h1[0]],
                  ('Job TTS',),
                  'best',
                  numpoints=1,
                  shadow=True,
                  prop=props)
    else:
        p1 = ax.plot(jobids, jobtts_list, 'o', color='b')
        ax.legend((p1),
                  ('Job TTS',),
                  'best',
                  numpoints=1,
                  shadow=True,
                  prop=props)

    fig.savefig(filename)

def _generate_stacked_vms2(c, node_events, run_name, graphtype='eps'):
    filename = _get_unique_graph_filename('ran-vms', run_name, graphtype)

    node_started_datetimes = node_events.get_event_datetimes_dict('node_started')
    new_node_datetimes = node_events.get_event_datetimes_dict('new_node')
    node_killed_datetimes = node_events.get_event_datetimes_dict('terminated_node')
    node_reconfigured_datetimes = node_events.get_event_datetimes_dict('reconfigured')

    begin = _get_eval_begin_datetime(node_started_datetimes,
                                     node_killed_datetimes,
                                     new_node_datetimes)
    end = _get_eval_end_datetime(node_started_datetimes,
                                 node_killed_datetimes,
                                 new_node_datetimes)

    seconds = _get_eval_seconds_list(begin, end)

    killed_vms_list = _get_killed_vms_list(node_events,
                                           seconds,
                                           begin,
                                           node_killed_datetimes)
    running_vms_list = _get_running_vms_list(node_events,
                                             seconds,
                                             begin,
                                             node_started_datetimes,
                                             node_killed_datetimes)
    launched_vms_list = _get_running_vms_list(node_events,
                                              seconds,
                                              begin,
                                              new_node_datetimes,
                                              node_killed_datetimes)
    reconfigured_list = _get_reconfigured_list(node_events,
                                               seconds,
                                               begin,
                                               node_reconfigured_datetimes)
    previous = 0
    for i,x in enumerate(reconfigured_list):
        if x > previous:
            reconfigured_list[i] = 8
            previous = 1
        else:
            reconfigured_list[i] = 0


    # Use the following block for trimming unecessary parts of the graph, if you had an extra long run e.g.
    #s1 = 100
    #s2 = 600
    #running_vms_list = running_vms_list[s1:s2]
    #killed_vms_list = killed_vms_list[s1:s2]
    #reconfigured_list = reconfigured_list[s1:s2]
    #launched_vms_list = launched_vms_list[s1:s2]
    #newseconds = seconds[s1:s2]
    #seconds = xrange(0,len(newseconds))

    # graph
    xmin = min(seconds)
    xmax = max(seconds)
    yminb = min(min(killed_vms_list), min(running_vms_list))
    ymaxb = max(max(killed_vms_list), max(running_vms_list)) + 2

    xstep = 60
    #xstep = int(xmax / 6)
    
    xvals = arange(xmin, xmax, xstep)

    fig = figure()

    clf()

    fig.suptitle('Instances',
                 verticalalignment='top',
                 horizontalalignment='center')

    axb = fig.add_subplot(1,1,1)
    axb.set_ylabel('Running / Killed VMs')
    axb.set_xlabel('Evaluation Second')
    axb.axis([xmin, xmax, yminb, ymaxb])
    pb1 = axb.plot(seconds,
                   running_vms_list, 'b',
                   label='Running VMs')
    pb2 = axb.plot(seconds,
                   killed_vms_list, 'ro',
                   label='Killed VMs')
    pb3 = axb.plot(seconds,
                   reconfigured_list, 'go',
                   label='Reconfigured')
    pb4 = axb.plot(seconds,
                   launched_vms_list, 'k--',
                   label='Launched')
    axb.legend((pb4, pb1, pb2, pb3), ('Launched VMs', 'Running VMs', 'Killed VMs', 'New Policy'), loc=7, prop=props)
    axb.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)
    xticks(xvals)

    fig.savefig(filename)
    c.log.info("Wrote file: %s" % filename)

def _generate_stacked_vms(workloadtype, log_events, node_events, run_name, graphtype='eps'):
    filename = _get_unique_graph_filename('stacked-vms', run_name, graphtype)

    node_started_datetimes = node_events.get_event_datetimes_dict('node_started') 
    new_node_datetimes = node_events.get_event_datetimes_dict('new_node') 
    if workloadtype == 'torque':
        node_killed_datetimes = node_events.get_event_datetimes_dict('terminated_node')
    else:
        node_killed_datetimes = node_events.get_event_datetimes_dict('fetch_killed') 
    jobs_begin_datetimes = log_events.get_event_datetimes_dict('job_begin')
    jobs_completed_datetimes = log_events.get_event_datetimes_dict('job_end')
    jobs_sent_datetimes = log_events.get_event_datetimes_dict('job_sent')

    begin = _get_eval_begin_datetime(node_started_datetimes,
                                     node_killed_datetimes,
                                     new_node_datetimes,
                                     jobs_completed_datetimes,
                                     jobs_sent_datetimes)
    end = _get_eval_end_datetime(node_started_datetimes,
                                 node_killed_datetimes,
                                 new_node_datetimes,
                                 jobs_completed_datetimes,
                                 jobs_sent_datetimes)

    seconds = _get_eval_seconds_list(begin, end)

    killed_vms_list = _get_killed_vms_list(node_events,
                                           seconds,
                                           begin,
                                           node_killed_datetimes)
    running_vms_list = _get_running_vms_list(node_events,
                                             seconds,
                                             begin,
                                             node_started_datetimes,
                                             node_killed_datetimes)

    jobs_completed_list = _get_jobs_list(log_events,
                                         seconds,
                                         begin,
                                         jobs_completed_datetimes)
    jobs_sent_list = _get_jobs_list(log_events,
                                    seconds,
                                    begin,
                                    jobs_sent_datetimes)
    jobs_running_list = _get_jobs_running_list(log_events,
                                               seconds,
                                               begin,
                                               jobs_begin_datetimes,
                                               jobs_completed_datetimes)
    jobs_queued_list = _get_jobs_queued_list(log_events,
                                             seconds,
                                             begin,
                                             jobs_sent_datetimes,
                                             jobs_begin_datetimes)

    # graph
    xmin = min(seconds)
    xmax = max(seconds)
    yminb = min(min(killed_vms_list), min(running_vms_list))
    ymaxb = max(max(killed_vms_list), max(running_vms_list)) + 2

    ymint = min(min(jobs_completed_list),
                min(jobs_sent_list),
                min(jobs_queued_list))
    ymaxt = max(max(jobs_completed_list),
                max(jobs_sent_list),
                max(jobs_running_list)) + 2

    ymint_1 = min(jobs_running_list)
    ymaxt_1 = max(jobs_running_list) + 2

    if ymaxt_1 >= (ymaxt - 10):
        ymaxt_1 = ymaxt

    xstep = 100
    xvals = arange(xmin, xmax, xstep)

    fig = figure()

    clf()

    fig.suptitle('Jobs and Instances',
                 verticalalignment='top',
                 horizontalalignment='center')

    # bottom graph
    axb = fig.add_subplot(2,1,2)
    axb.set_ylabel('Running / Killed VMs')
    axb.set_xlabel('Evaluation Second')
    axb.axis([xmin, xmax, yminb, ymaxb])
    pb1 = axb.plot(seconds,
                   running_vms_list,
                   label='Running VMs',
                   color='b')
    pb2 = axb.plot(seconds,
                   killed_vms_list,
                   label='Killed VMs',
                   color='r')
    axb.legend((pb1, pb2), ('Running VMs', 'Killed VMs'), 'upper left', prop=props)
    axb.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)

    # top graph
    axt = fig.add_subplot(2,1,1)
    axt.set_ylabel('Submitted / Queued / Completed')
    axt.set_xlabel('Evaluation Second')
    axt.axis([xmin, xmax, ymint, ymaxt])
    ylim(ymax=ymaxt)
    pt1 = axt.plot(seconds,
                   jobs_completed_list,
                   label='Jobs Completed',
                   color='g',
                   linestyle=':')
    pt2 = axt.plot(seconds,
                   jobs_sent_list,
                   label='Jobs Submitted',
                   color='k')
    pt3 = axt.plot(seconds,
                   jobs_queued_list, 
                   label='Jobs Queued',
                   color='r',
                   linestyle='--')
    
    axt_1 = axt.twinx()
    axt_1.set_ylabel('Running')
    axt_1.axis([xmin, xmax, ymint_1, ymaxt_1])
    pt4 = axt_1.plot(seconds,
                     jobs_running_list,
                     label='Jobs Running',
                     color='b',
                     linestyle='-.')

    axt.legend((pt1, pt2, pt3, pt4), ('Jobs Completed',
                                 'Jobs Submitted',
                                 'Jobs Queued',
                                 'Jobs Running'), 'center left', prop=props)
    axt.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)

    fig.savefig(filename)

def _generate_job_rate(workloadtype, log_events, node_events, run_name, graphtype='eps'):
    filename = _get_unique_graph_filename('job-rate', run_name, graphtype)

    node_started_datetimes = node_events.get_event_datetimes_dict('node_started') 
    new_node_datetimes = node_events.get_event_datetimes_dict('new_node') 
    if workloadtype == 'torque':
        node_killed_datetimes = node_events.get_event_datetimes_dict('terminated_node')
    else:
        node_killed_datetimes = node_events.get_event_datetimes_dict('fetch_killed') 
    jobs_completed_datetimes = log_events.get_event_datetimes_dict('job_end')

    begin = _get_eval_begin_datetime(node_started_datetimes,
                                     node_killed_datetimes,
                                     new_node_datetimes,
                                     jobs_completed_datetimes)
    end = _get_eval_end_datetime(node_started_datetimes,
                                 node_killed_datetimes,
                                 new_node_datetimes,
                                 jobs_completed_datetimes)

    seconds = _get_eval_seconds_list(begin, end)

    killed_vms_list = _get_killed_vms_list(node_events,
                                           seconds,
                                           begin,
                                           node_killed_datetimes)
    running_vms_list = _get_running_vms_list(node_events,
                                             seconds,
                                             begin,
                                             node_started_datetimes,
                                             node_killed_datetimes)

    # get number of jobs completed each second
    jobs_completed_rate_list = _get_job_rate_from_file(log_events,
                                                       node_events,
                                                       begin,
                                                       seconds)

    log_events.c.log.info("Total jobs completed: %s" % sum(jobs_completed_rate_list))

    # graph
    xmin = min(seconds)
    xmax = max(seconds)
    yminb = min(min(killed_vms_list), min(running_vms_list))
    ymaxb = max(max(killed_vms_list), max(running_vms_list)) + 2

    ymint = min(jobs_completed_rate_list)
    ymaxt = max(jobs_completed_rate_list) + 2

    xstep = 500
    xvals = arange(xmin, xmax, xstep)

    fig = figure()

    clf()

    fig.suptitle('Job Rate and Instances',
                 verticalalignment='top',
                 horizontalalignment='center')

    # bottom graph
    axb = fig.add_subplot(2,1,2)
    axb.set_ylabel('Running / Killed VMs')
    axb.set_xlabel('Evaluation Second')
    axb.axis([xmin, xmax, yminb, ymaxb])
    pb1 = axb.plot(seconds,
                   running_vms_list,
                   label='Running VMs',
                   color='b')
    pb2 = axb.plot(seconds,
                   killed_vms_list,
                   label='Killed VMs',
                   color='r')
    axb.legend((pb1, pb2), ('Running VMs', 'Killed VMs'), 'lower center', prop=props)
    axb.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)

    # top graph
    axt = fig.add_subplot(2,1,1)
    axt.set_ylabel('Job Throughput')
    axt.set_xlabel('Evaluation Second')
    axt.axis([xmin, xmax, ymint, ymaxt])
    pt1 = axt.plot(seconds,
                   jobs_completed_rate_list,
                   label='Job Rate',
                   color='b',
                   linestyle=':')

    axt.legend((pt1,), ('Jobs Completed (per second)',), 'best', prop=props)
    axt.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)

    fig.savefig(filename)

def _generate_node_info(workloadtype, log_events, node_events, run_name, graphtype='eps'):
    filename = _get_unique_graph_filename('node-info', run_name, graphtype)

    new_node_datetimes = node_events.get_event_datetimes_dict('new_node')

    ctxdone_datetimes = node_events.get_event_datetimes_dict('launch_ctx_done')
    node_started_datetimes = node_events.get_event_datetimes_dict('node_started') 

    # sort node ids by their datetime value
    nodeids = []
    for pair in sorted(new_node_datetimes.items(), key=itemgetter(1)):
        nodeids.append(pair[0])

    nodeids, ctxdone_list, nodestarted_list = _get_nodeinfo_list(log_events,
                                                                 nodeids,
                                                                 ctxdone_datetimes,
                                                                 node_started_datetimes,
                                                                 new_node_datetimes)

    # graph
    nice_nodeids = range(len(nodeids))
    xmin = min(nice_nodeids)
    xmax = max(nice_nodeids)
    ymin = min(ctxdone_list)
    ymax = max(ctxdone_list)

    fig = figure()

    clf()

    fig.suptitle('Node Information (relative to new_node event)',
                 verticalalignment='top',
                 horizontalalignment='center')

    # bottom graph
    ax = fig.add_subplot(1,1,1)
    ax.set_ylabel('Seconds')
    ax.set_xlabel('Node ID')
    ax.axis([xmin, xmax, ymin, ymax])
    if len(nice_nodeids) <= 20:
        xticks(nice_nodeids)
    ylim(0, ymax)
    h1 = ax.plot(nice_nodeids, ctxdone_list, 's', color='r')
    h2 = ax.plot(nice_nodeids, nodestarted_list, 'o', color='b')
    ax.legend([h1[0], h2[0]],
              ('launch_ctx_done', 'node_started'),
              'best',
              numpoints=1,
              shadow=True,
              prop=props)

    fig.savefig(filename)

def _generate_controller(workloadtype,
                         log_events,
                         node_events,
                         controller_events,
                         run_name,
                         graphtype='eps'):
    filename = _get_unique_graph_filename('controller', run_name, graphtype)

    node_started_datetimes = node_events.get_event_datetimes_dict('node_started') 
    if workloadtype == 'torque':
        node_killed_datetimes = node_events.get_event_datetimes_dict('terminated_node')
    else:
        node_killed_datetimes = node_events.get_event_datetimes_dict('fetch_killed') 
    job_sent_datetimes = log_events.get_event_datetimes_dict('job_sent')
    job_begin_datetimes = log_events.get_event_datetimes_dict('job_begin')

    ec_start_datetimes = controller_events.get_event_datetimes_list('EPU_CONTROLLER_START')
    ec_end_datetimes = controller_events.get_event_datetimes_list('EPU_CONTROLLER_TERMINATE')

    begin = _get_eval_begin_datetime(node_started_datetimes,
                                     node_killed_datetimes,
                                     job_sent_datetimes,
                                     job_begin_datetimes)
    end = _get_eval_end_datetime(node_started_datetimes,
                                 node_killed_datetimes,
                                 job_sent_datetimes,
                                 job_begin_datetimes)

    seconds = _get_eval_seconds_list(begin, end)

    killed_vms_list = _get_killed_vms_list(node_events,
                                           seconds,
                                           begin,
                                           node_killed_datetimes)
    running_vms_list = _get_running_vms_list(node_events,
                                             seconds,
                                             begin,
                                             node_started_datetimes,
                                             node_killed_datetimes)

    job_sent_list = _get_jobs_list(log_events,
                                   seconds,
                                   begin,
                                   job_sent_datetimes)

    killed_controller_list = _get_killed_controller_list(seconds,
                                                         begin,
                                                         ec_end_datetimes)
    running_controller_list = _get_running_controller_list(seconds,
                                                           begin,
                                                           ec_start_datetimes,
                                                           ec_end_datetimes)
    #print running_controller_list
    # graph
    xmin = min(seconds)
    xmax = max(seconds)
    yminb = min(killed_controller_list)
    ymaxb = max(running_controller_list) + 1

    ymint = min(min(killed_vms_list), min(running_vms_list), min(job_sent_list))
    ymaxt = max(max(killed_vms_list), max(running_vms_list), max(job_sent_list)) + 1


    xstep = 250
    xvals = arange(xmin, xmax, xstep)

    fig = figure()

    clf()

    fig.suptitle('EPU Controller Recovery',
                 verticalalignment='top',
                 horizontalalignment='center')

    # bottom graph
    axb = fig.add_subplot(2,1,2)
    axb.set_ylabel('Controllers')
    axb.set_xlabel('Evaluation Second')
    axb.axis([xmin, xmax, yminb, ymaxb])
    pb1 = axb.plot(seconds,
                   running_controller_list,
                   label='Running Controllers',
                   color='b')
    pb2 = axb.plot(seconds,
                   killed_controller_list,
                   label='Killed Controllers',
                   color='r')
    axb.legend((pb1, pb2), ('Running Controllers', 'Killed Controllers'),
                         'upper left', prop=props)
    axb.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    yticks([0,1,2])
    xticks(xvals)

    # top graph
    axt = fig.add_subplot(2,1,1)
    axt.set_ylabel('Submitted Jobs / Running VMs')
    axt.set_xlabel('Evaluation Second')
    axt.axis([xmin, xmax, ymint, ymaxt])
    ylim(ymax=ymaxt)
    pt1 = axt.plot(seconds,
                   job_sent_list,
                   label='Jobs Submitted',
                   color='g',
                   linestyle=':')
    pt2 = axt.plot(seconds,
                   running_vms_list,
                   label='Running VMs',
                   color='b')

    axt.legend((pt1, pt2), ('Jobs Submitted',
                            'Running VMs'), 'upper left', prop=props)
    axt.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)

    fig.savefig(filename)

def generate_graph(p, c, m, run_name):

    validate(p)

    graphname = p.get_arg_or_none('graphname')
    graphtype = p.get_arg_or_none('graphtype')
    workloadtype = p.get_arg_or_none('workloadtype')
    workloadtype = workloadtype.lower()

    node_events = NodeEvents(p, c, m, run_name)
    controller_events = ControllerEvents(p, c, m, run_name)
    if workloadtype == 'torque':
        log_events = TorqueEvents(p, c, m, run_name)
    else:
        log_events = AmqpEvents(p, c, m, run_name)

    if 'stacked-vms' == graphname:
        _generate_stacked_vms(workloadtype, log_events, node_events, run_name, graphtype)
    elif 'stacked-vms2' == graphname:
        _generate_stacked_vms2(c, node_events, run_name, graphtype)
    elif 'job-tts' == graphname:
        _generate_job_tts(log_events, node_events, run_name, graphtype)
    elif 'job-rate' == graphname:
        _generate_job_rate(workloadtype, log_events, node_events, run_name, graphtype)
    elif 'node-info' == graphname:
        _generate_node_info(workloadtype, log_events, node_events, run_name, graphtype)
    elif 'controller' == graphname:
        _generate_controller(workloadtype,
                             log_events,
                             node_events,
                             controller_events,
                             run_name,
                             graphtype)
    else:
        raise InvalidInput('Unrecognized graph name, must be stacked-vms, ' + \
                           'job-tts, job-rate, node-info, or controller.')
