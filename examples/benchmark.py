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
from pycpa import schedulers as pycpaschedulers
from taskchain import schedulers as taskchainschedulers
from taskchain import path_analysis as taskchainpath_analysis

import csv
import itertools

def run(scheduler, priorities):
    assert(len(priorities) >= 6)
    # generate an new system
    s = model.System()

    # add two resources (CPUs) to the system
    # and register the static priority preemptive scheduler
    r1 = s.bind_resource(model.Resource("R1", scheduler))

    # create and bind tasks to r1
    t11 = r1.bind_task(model.Task("T11", wcet=10, bcet=1, scheduling_parameter=priorities[0]))
    t21 = r1.bind_task(model.Task("T21", wcet=2, bcet=2, scheduling_parameter=priorities[1]))
    t31 = r1.bind_task(model.Task("T31", wcet=4, bcet=2, scheduling_parameter=priorities[2]))

    t12 = r1.bind_task(model.Task("T12", wcet=3, bcet=1, scheduling_parameter=priorities[3]))
    t22 = r1.bind_task(model.Task("T22", wcet=9, bcet=4, scheduling_parameter=priorities[4]))
    t32 = r1.bind_task(model.Task("T32", wcet=5, bcet=3, scheduling_parameter=priorities[5]))

    # specify precedence constraints: T11 -> T21 -> T31; T12-> T22 -> T32
    t11.link_dependent_task(t21)
    t21.link_dependent_task(t31)

    t12.link_dependent_task(t22)
    t22.link_dependent_task(t32)

    # register a periodic with jitter event model for T11 and T12
    t11.in_event_model = model.PJdEventModel(P=20, J=5)
    t12.in_event_model = model.PJdEventModel(P=100, J=0)

    # register a task chain as a stream
    s1 = s.bind_path(model.Path("S1", [t11, t21, t31]))
    s2 = s.bind_path(model.Path("S2", [t12, t22, t32]))

    # perform the analysis
    print("Performing analysis")
    task_results = analysis.analyze_system(s)

    return [task_results, [s1, s2]]

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    with open("path_report.csv", "wb") as csvfile:
        pathwriter = csv.writer(csvfile, delimiter='\t')
        pathwriter.writerow(["Path", "P1", "P2", "P3", "P4", "P5", "P6", "lat1", "lat2", "lat3"])
        pathnames = ["S1", "S2"]

        with open("wcrt_report.csv", "wb") as csvfile:
            wcrtwriter = csv.writer(csvfile, delimiter='\t')
            wcrtwriter.writerow(["P1", "P2", "P3", "P4", "P5", "P6", "T1a", "T1b", "T2a", "T2b",
                "T3a", "T3b", "T4a", "T4b", "T5a", "T5b", "T6a", "T6b"])

            for priorities in itertools.permutations([1,2,3,4,5,6]):
                print("Running analyses for priorities %s" % str(priorities))
                try:
                    [results1,paths1] = run(pycpaschedulers.SPPScheduler(), priorities)
                except analysis.NotSchedulableException as e:
                    print(e)
                    results1 = dict()
                    paths1 = None

                [results2,paths2] = run(taskchainschedulers.SPPScheduler(), priorities)
                [results3,paths3] = run(taskchainschedulers.ChainScheduler(), priorities)

                wcrt1 = dict()
                wcrt2 = dict()
                for t1 in results1:
                    for t2 in results2:
                        if t1.name == t2.name:
                            wcrt1[t1.name] = results1[t1].wcrt
                            wcrt2[t2.name] = results2[t2].wcrt
                            if results2[t2].wcrt > results1[t1].wcrt:
                                print("WCRT of task %s is worse in second experiment" % (t1.name))

                if len(wcrt1) > 0:
                    wcrtwriter.writerow([priorities[0],
                                         priorities[1],
                                         priorities[2],
                                         priorities[3],
                                         priorities[4],
                                         priorities[5],
                                         wcrt1["T11"],
                                         wcrt2["T11"],
                                         wcrt1["T21"],
                                         wcrt2["T21"],
                                         wcrt1["T31"],
                                         wcrt2["T31"],
                                         wcrt1["T12"],
                                         wcrt2["T12"],
                                         wcrt1["T22"],
                                         wcrt2["T22"],
                                         wcrt1["T32"],
                                         wcrt2["T32"]])

                # Calculate e2e latency
                for i in range(0, 2):
                    if paths1 != None:
                        [tmp, l1] = path_analysis.end_to_end_latency(paths1[i], results1)
                    else:
                        l1 = 0

                    if paths2 != None:
                        [tmp, l2] = path_analysis.end_to_end_latency(paths2[i], results2)
                    else:
                        l2 = 0

                    if paths3 != None:
                        [tmp, l3] = taskchainpath_analysis.end_to_end_latency(paths3[i], results3)
                    else:
                        l3 = 0

                    pathwriter.writerow([pathnames[i], priorities[0],
                                                       priorities[1],
                                                       priorities[2],
                                                       priorities[3],
                                                       priorities[4],
                                                       priorities[5],
                                                       l1,l2,l3])
