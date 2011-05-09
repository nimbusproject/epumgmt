from pylab import *
import matplotlib
import os

from epumgmt.defaults.log_events import AmqpEvents, TorqueEvents, NodeEvents

props = matplotlib.font_manager.FontProperties(size=10)

def _convert_datetime_to_seconds(dateTime):
    seconds = (dateTime.microseconds + \
              (dateTime.seconds + dateTime.days * 24 * 3600) \
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
    firsttime = _get_first_datetime(args[0])
    for arg in args:
        for key in arg.keys():
            if firsttime > arg[key]:
                firsttime = arg[key]
    return firsttime
            
def _get_eval_end_datetime(*args):
    if len(args) <= 0:
        return
    lasttime = _get_last_datetime(args[0])
    for arg in args:
        for key in arg.keys():
            if lasttime < arg[key]:
                lasttime = arg[key]
    return lasttime

def _get_unique_graph_filename(key, run_name, filetype):
    basedir = os.path.abspath('.')
    filenum = 0
    filename = os.path.join(basedir, \
                            run_name + '-' + \
                            key + '-' + \
                            str(filenum) + '.' + \
                            filetype)
    while os.path.exists(filename):
        filenum += 1
        filename = os.path.join(basedir, \
                                run_name + '-' + \
                                key + '-' + \
                                str(filenum) + '.' + \
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

def _get_running_vms_list(log_events, \
                          seconds, \
                          begin, \
                          start_datetimes, \
                          killed_datetimes):
    runningvms = {}
    for second in seconds:
        runningvms[second] = 0

    for key in start_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, start_datetimes[key])
        if (diff >= 0) and (diff <= max(seconds)):
            second = diff
            while second <= max(seconds):
                runningvms[second] += 1
                second += 1
        else:
            log_events.c.log.error('running vm time does not appear to be ' + \
                                   'valid: %s' % diff)
    for key in killed_datetimes.keys(): 
        diff = _get_datetime_diff_seconds(begin, killed_datetimes[key])
        if (diff >= 0) and (diff <= max(seconds)):
            second = diff
            while second <= max(seconds):
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

    for key in job_begin_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_begin_datetimes[key])
        if (diff >= 0) and (diff <= max(seconds)):
            second = diff
            while second <= max(seconds):
                jobs[second] += 1
                second += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    for key in job_end_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_end_datetimes[key])
        if (diff >= 0) and (diff <= max(seconds)):
            second = diff
            while second <= max(seconds):
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

def _get_jobs_queued_list(log_events,
                          seconds,
                          begin,
                          job_sent_datetimes,
                          job_begin_datetimes):
    jobs = {}
    for second in seconds:
        jobs[second] = 0

    for key in job_sent_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_sent_datetimes[key])
        if (diff >= 0) and (diff <= max(seconds)):
            second = diff
            while second <= max(seconds):
                jobs[second] += 1
                second += 1
        else:
            log_events.c.log.error('job time does not appear to be ' + \
                                   'valid: %s' % diff)

    for key in job_begin_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_begin_datetimes[key])
        if (diff >= 0) and (diff <= max(seconds)):
            second = diff
            while second <= max(seconds):
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

    for key in job_datetimes.keys():
        diff = _get_datetime_diff_seconds(begin, job_datetimes[key])
        if (diff >= 0) and (diff <= max(seconds)):
            second = diff
            while second <= max(seconds):
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

# not done:
#    - "contextualization begins"
#    - "node request recognized"
def _generate_job_tts(log_events, node_events, run_name, graphtype='eps'):
    filename = _get_unique_graph_filename('job-tts', run_name, graphtype)

    job_begin_datetimes = log_events.get_event_datetimes_dict('job_begin')
    job_sent_datetimes = log_events.get_event_datetimes_dict('job_sent')

    jobids = job_sent_datetimes.keys()
    jobids.sort()

    jobtts_list = _get_jobtts_list(log_events, \
                                   job_begin_datetimes, \
                                   job_sent_datetimes)

    # graph
    xmin = min(jobids)
    xmax = max(jobids)
    ymin = min(jobtts_list)
    ymax = max(jobtts_list)

    fig = figure()

    clf()

    fig.suptitle('Job Time to Start', \
                 verticalalignment='top', \
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

    begin = _get_eval_begin_datetime(node_started_datetimes, \
                                     node_killed_datetimes, \
                                     new_node_datetimes, \
                                     jobs_completed_datetimes, \
                                     jobs_sent_datetimes)
    end = _get_eval_end_datetime(node_started_datetimes, \
                                 node_killed_datetimes, \
                                 new_node_datetimes, \
                                 jobs_completed_datetimes, \
                                 jobs_sent_datetimes)

    seconds = _get_eval_seconds_list(begin, end)

    killed_vms_list = _get_killed_vms_list(node_events, \
                                           seconds, \
                                           begin, \
                                           node_killed_datetimes)
    running_vms_list = _get_running_vms_list(node_events, \
                                             seconds, \
                                             begin, \
                                             node_started_datetimes, \
                                             node_killed_datetimes)

    jobs_completed_list = _get_jobs_list(log_events, \
                                         seconds, \
                                         begin, \
                                         jobs_completed_datetimes)
    jobs_sent_list = _get_jobs_list(log_events, \
                                    seconds, \
                                    begin, \
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
    ymaxb = max(max(killed_vms_list), max(running_vms_list)) 

    ymint = min(min(jobs_completed_list),
                min(jobs_sent_list),
                min(jobs_queued_list))
    ymaxt = max(max(jobs_completed_list),
                max(jobs_sent_list),
                max(jobs_running_list))

    ymint_1 = min(jobs_running_list)
    ymaxt_1 = max(jobs_running_list)

    if ymaxt_1 >= (ymaxt - 10):
        ymaxt_1 = ymaxt

    xstep = 100
    xvals = arange(xmin, xmax, xstep)

    fig = figure()

    clf()

    fig.suptitle('Jobs and Instances', \
                 verticalalignment='top', \
                 horizontalalignment='center')

    # bottom graph
    axb = fig.add_subplot(2,1,2)
    axb.set_ylabel('Running / Killed VMs')
    axb.set_xlabel('Evaluation Second')
    axb.axis([xmin, xmax, yminb, ymaxb])
    pb1 = axb.plot(seconds, \
                   running_vms_list, \
                   label='Running VMs', \
                   color='b')
    pb2 = axb.plot(seconds, \
                   killed_vms_list, \
                   label='Killed VMs', \
                   color='r')
    axb.legend((pb1, pb2), ('Running VMs', 'Killed VMs'), 'best', prop=props)
    axb.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)

    # top graph
    axt = fig.add_subplot(2,1,1)
    axt.set_ylabel('Submitted / Queued / Completed')
    axt.set_xlabel('Evaluation Second')
    axb.axis([xmin, xmax, ymint, ymaxt])
    pt1 = axt.plot(seconds, \
                   jobs_completed_list, \
                   label='Jobs Completed', \
                   color='g',
                   linestyle=':')
    pt2 = axt.plot(seconds, \
                   jobs_sent_list, \
                   label='Jobs Submitted', \
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
                                 'Jobs Running'), 'best', prop=props)
    axt.locator_params(axis='x', tight=True, nbins=xmax/xstep)
    xticks(xvals)

    fig.savefig(filename)

def generate_graph(p, c, m, run_name):
    graphname = p.get_arg_or_none('graphname')
    graphtype = p.get_arg_or_none('graphtype')
    workloadtype = p.get_arg_or_none('workloadtype').lower()
    if not workloadtype:
        c.log.error('Expecting workloadtype to be specified.')
        return

    node_events = NodeEvents(p, c, m, run_name)
    if workloadtype == 'torque':
        log_events = TorqueEvents(p, c, m, run_name)
    else:
        log_events = AmqpEvents(p, c, m, run_name)

    if 'stacked-vms' == graphname:
        _generate_stacked_vms(workloadtype, log_events, node_events, run_name, graphtype)
    elif 'job-tts' == graphname:
        _generate_job_tts(log_events, node_events, run_name, graphtype)
    else:
        c.log.error('Unrecognized graph name, must be stacked-vms ' + \
                    'or job-tts')
