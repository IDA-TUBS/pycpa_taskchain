"""
| Copyright (C) 2015 Johannes Schlatow
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Johannes Schlatow

Description
-----------

Benchmark script
"""

from pycpa import model
from pycpa import analysis
from pycpa import path_analysis
from pycpa import graph
from pycpa import options
from pycpa import schedulers 
from taskchain import model as tc_model
from taskchain import schedulers as tc_schedulers

import csv
import itertools

def run(scheduler, priorities, create_chains=True):
    assert(len(priorities) >= 6)
    # generate an new system
    s = model.System()

    # add two resources (CPUs) to the system
    # and register the static priority preemptive scheduler
    r1 = s.bind_resource(tc_model.TaskchainResource("R1", scheduler()))

    # create and bind tasks to r1
    t11 = r1.bind_task(model.Task("P1", wcet=3, bcet=1, scheduling_parameter=priorities[0],
        synchronous_call=False))
    t12 = r1.bind_task(model.Task("TC1", wcet=5, bcet=1, scheduling_parameter=priorities[1],
        synchronous_call=True))
    t13 = r1.bind_task(model.Task("O2OR", wcet=50, bcet=10, scheduling_parameter=priorities[2],
        synchronous_call=True))
    t14 = r1.bind_task(model.Task("TC2", wcet=5, bcet=1, scheduling_parameter=priorities[1],
        synchronous_call=True))
    t15 = r1.bind_task(model.Task("P2", wcet=7, bcet=1, scheduling_parameter=priorities[0],
        synchronous_call=True))

    t21 = r1.bind_task(model.Task("LA1", wcet=3, bcet=1, scheduling_parameter=priorities[3],
        synchronous_call=False))
    t22 = r1.bind_task(model.Task("O1OR", wcet=10, bcet=5, scheduling_parameter=priorities[4],
        synchronous_call=True))
    t23 = r1.bind_task(model.Task("LA2", wcet=3, bcet=1, scheduling_parameter=priorities[3],
        synchronous_call=True))
    t24 = r1.bind_task(model.Task("OM", wcet=10, bcet=5, scheduling_parameter=priorities[5],
        synchronous_call=True))
    t25 = r1.bind_task(model.Task("LA3", wcet=10, bcet=5, scheduling_parameter=priorities[3],
        synchronous_call=True))
    t26 = r1.bind_task(model.Task("S", wcet=10, bcet=5, scheduling_parameter=priorities[6],
        synchronous_call=True))
    t27 = r1.bind_task(model.Task("LA4", wcet=4, bcet=1, scheduling_parameter=priorities[3],
        synchronous_call=True))

    # specify precedence constraints
    t11.link_dependent_task(t12).link_dependent_task(t13).link_dependent_task(t14).link_dependent_task(t15)
    t21.link_dependent_task(t22).link_dependent_task(t23).link_dependent_task(t24).link_dependent_task(t25).link_dependent_task(t26).link_dependent_task(t27)

    # register a periodic with jitter event model for T11 and T12
    t11.in_event_model = model.PJdEventModel(P=200, J=5)
    t21.in_event_model = model.PJdEventModel(P=100, J=5)

    # register task chains as a path
    s1 = s.bind_path(model.Path("S1", [t11, t12, t13, t14, t15]))
    s2 = s.bind_path(model.Path("S2", [t21, t22, t23, t24, t25, t26, t27]))

    if create_chains:
        # register task chains
        c1 = r1.bind_taskchain(tc_model.Taskchain("C1", [t11, t12, t13, t14, t15]))
        c2 = r1.bind_taskchain(tc_model.Taskchain("C2", [t21, t22, t23, t24, t25, t26, t27]))

    # perform the analysis
    print("Performing analysis")
    task_results = analysis.analyze_system(s)

    return (task_results, [s1, s2])

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    with open("path_report_parkassist.csv", "wb") as csvfile:
        pathwriter = csv.writer(csvfile, delimiter='\t')
        pathwriter.writerow(["Path", "P1", "P2", "P3", "P4", "P5", "P6", "P7",
                             "lat", "lat_sync", "lat_syncref", "lat_async"])
        pathnames = ["S1", "S2"]

        for priorities in itertools.permutations([1,2,3,4,5,6,7]):
            print("Running analyses for priorities %s" % str(priorities))
            paths = None
            paths_sync = None
            paths_syncref = None
            paths_async = None

            try:
                [results,paths]                 = run(schedulers.SPPScheduler,        priorities, False)
            except analysis.NotSchedulableException as e:
                print(e)

            try:
                [results_sync,paths_sync]       = run(tc_schedulers.SPPSchedulerSync, priorities)
            except analysis.NotSchedulableException as e:
                print(e)

            try:
                [results_syncref,paths_syncref] = run(tc_schedulers.SPPSchedulerSyncRefined, priorities)
            except analysis.NotSchedulableException as e:
                print(e)

            try:
                [results_async,paths_async]     = run(tc_schedulers.SPPSchedulerAsync,       priorities)
            except analysis.NotSchedulableException as e:
                print(e)

            # Calculate e2e latency
            for i in range(0, len(pathnames)):
                l         = 0
                l_sync    = 0
                l_syncref = 0
                l_async   = 0
                n = 1

                if paths != None:
                    [tmp, l] = path_analysis.end_to_end_latency(paths[i], results, n)
                if paths_sync != None:
                    [tmp, l_sync] = path_analysis.end_to_end_latency(paths_sync[i], results_sync, n)
                if paths_syncref != None:
                    [tmp, l_syncref] = path_analysis.end_to_end_latency(paths_syncref[i], results_syncref, n)
                if paths_async != None:
                    [tmp, l_async] = path_analysis.end_to_end_latency(paths_async[i], results_async, n)

                if l > 0 and l < l_sync:
                    print("Warning: Improved (sync) latency result is actually worse!")
                if l_sync > 0 and l_sync < l_syncref:
                    print("Warning: Improved (refined) latency result is actually worse!")
                if l > 0 and l < l_async:
                    print("Warning: Improved (async) latency result is actually worse!")

                pathwriter.writerow([pathnames[i], priorities[0],
                                                   priorities[1],
                                                   priorities[2],
                                                   priorities[3],
                                                   priorities[4],
                                                   priorities[5],
                                                   priorities[6],
                                                   l,
                                                   l_sync,
                                                   l_syncref,
                                                   l_async])
