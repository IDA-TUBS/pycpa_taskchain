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
from taskchain import path_analysis as taskchainpath_analysis

import csv
import itertools

def run(priorities, scheduler=schedulers.SPPScheduler()):
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
        pathwriter.writerow(["Path", "P1", "P2", "P3", "P4", "P5", "P6", "lat1a", "lat1b", "lat2a",
            "lat2b", "lat3a", "lat3b", "lat4a", "lat4b", "lat5a", "lat5b"])
        pathnames = ["S1", "S2"]

        for priorities in itertools.permutations([1,2,3,4,5,6]):
            print("Running analyses for priorities %s" % str(priorities))
            try:
                [results,paths] = run(priorities)
            except analysis.NotSchedulableException as e:
                print(e)
                results = dict()
                paths = None

            # Calculate e2e latency
            for i in range(0, len(pathnames)):
                l_old = dict()
                l_new = dict()
                for n in range(0,5):
                    if paths != None:
                        [tmp, l_old[n]] = path_analysis.end_to_end_latency(paths[i], results, n)
                        [tmp, l_new[n]] = taskchainpath_analysis.end_to_end_latency(paths[i], results, n)
                    else:
                        l_old[n] = 0
                        l_new[n] = 0

                    if l_old[n] < l_new[n]:
                        print("Warning: Improved latency result is actually worse!")

                pathwriter.writerow([pathnames[i], priorities[0],
                                                   priorities[1],
                                                   priorities[2],
                                                   priorities[3],
                                                   priorities[4],
                                                   priorities[5],
                                                   l_old[0],
                                                   l_new[0],
                                                   l_old[1],
                                                   l_new[1],
                                                   l_old[2],
                                                   l_new[2],
                                                   l_old[3],
                                                   l_new[3],
                                                   l_old[4],
                                                   l_new[4]])
