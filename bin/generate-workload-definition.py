#! /usr/bin/env python

from optparse import OptionParser, OptionGroup
import sys

def check_options(options):
    rc = 0
    if options.killSeconds and options.killCounts:
        ksList = options.killSeconds.split(',')
        kcList = options.killCounts.split(',')
        if len(ksList) != len(kcList):
            sys.stderr.write('Length mismatch: --kill-seconds list must ' + \
                             'be the same length as --kill-counts.\n')
            rc = 1
    else:
        if options.killSeconds or options.killCounts:
            sys.stderr.write('You must specify both --kill-seconds and ' + \
                             '--kill-counts.')
            rc = 1
    if options.submitSeconds and options.submitCounts and options.submitSleep:
        ssList = options.submitSeconds.split(',')
        scList = options.submitCounts.split(',')
        slList = options.submitSleep.split(',')
        if (len(ssList) != len(scList)) or \
           (len(ssList) != len(slList)):
            sys.stderr.write('Length mismatch: --submit-seconds, ' + \
                             '--submit-counts, and --submit-sleep lists ' + \
                             'must all be the same length.\n')
            rc = 1
    else:
        if options.submitSeconds or \
           options.submitCounts or \
           options.submitSleep:
            sys.stderr.write('You must specify --submit-seconds, ' + \
                             '--submit-counts and --submit-sleep.')
            rc = 1
    return rc

def parse_options():
    parser = OptionParser()

    parser.add_option('--kill-seconds', dest='killSeconds', \
                      help='Seconds to wait before killing VMs. This ' + \
                      'may be a comma separated list, however, ' + \
                      'spaces are not allowed. The length of the list ' + \
                      'must match the list provided for --kill-counts.')
    parser.add_option('--kill-counts', dest='killCounts', \
                      help='Number of VMs to kill. This ' + \
                      'may be a comma separated list, however, ' + \
                      'spaces are not allowed. The length of the list ' + \
                      'must match the list provided for --kill-seconds.')
    parser.add_option('--kill-controller', dest='killController', \
                      help='Seconds to wait before killing a ' + \
                      'This may be a comma separated list.')
    parser.add_option('--submit-seconds', dest='submitSeconds', \
                      help='Seconds to wait before submitting tasks. This ' + \
                      'may be a comma separated list, however, ' + \
                      'spaces are not allowed. The length of the list ' + \
                      'must match the list provided for --submit-counts ' + \
                      'and --submit-sleep.')
    parser.add_option('--submit-counts', dest='submitCounts', \
                      help='Number of tasks to submit. This ' + \
                      'may be a comma separated list, however, ' + \
                      'spaces are not allowed. The length of the list ' + \
                      'must match the list provided for --submit-seconds ' + \
                      'and --submit-sleep.')
    parser.add_option('--submit-sleep', dest='submitSleep', \
                      help='Seconds for tasks to sleep. This ' + \
                      'may be a comma separated list, however, ' + \
                      'spaces are not allowed. The length of the list ' + \
                      'must match the list provided for --submit-seconds ' + \
                      'and --submit-counts.')
    parser.add_option('--first-batchid', dest='firstBatchID', \
                      help='The first batch ID to start with for ' + \
                      'submit tasks.')

    (options, args) = parser.parse_args()

    return options

def write_workload(killSeconds, \
                   killCounts, \
                   killController, \
                   submitSeconds, \
                   submitCounts, \
                   submitSleep, \
                   firstBatchID):
    controllerLine = 'KILL_CONTROLLER %s 1\n'
    killLine = 'KILL %s %s\n'
    submitLine = 'SUBMIT %s %s %s %s\n'
    if killController != None:
        cList = killController.split(',')
        listLen = len(cList)
        for i in range(listLen):
            sys.stdout.write(controllerLine % cList[i])
    if killSeconds != None and killCounts != None:
        ksList = killSeconds.split(',')
        kcList = killCounts.split(',')
        listLen = len(ksList)
        for i in range(listLen):
            sys.stdout.write(killLine % (ksList[i], kcList[i]))
    if (submitSeconds != None) and \
       (submitCounts != None) and \
       (submitSleep != None):
        ssList = submitSeconds.split(',')
        scList = submitCounts.split(',')
        slList = submitSleep.split(',')
        listLen = len(ssList)
        if not firstBatchID:
            firstBatchID = 0
        else:
            firstBatchID = int(firstBatchID)
        for i in range(listLen):
            sys.stdout.write(submitLine % (ssList[i], \
                                           scList[i], \
                                           slList[i], \
                                           firstBatchID))
            firstBatchID += int(scList[i])

def main():
    options = parse_options()
    if 1 == check_options(options):
        return 1
    write_workload(options.killSeconds, \
                   options.killCounts, \
                   options.killController, \
                   options.submitSeconds, \
                   options.submitCounts, \
                   options.submitSleep, \
                   options.firstBatchID)
    return 0

if __name__ == '__main__':
    sys.exit(main())
