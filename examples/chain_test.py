"""
| Copyright (C) 2015 Johannes Schlatow
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Johannes Schlatow

Description
-----------

Simple taskchain end-to-end latency test
"""

from pycpa import model
from pycpa import analysis
from pycpa import path_analysis
#from pycpa import schedulers
from pycpa import graph
from pycpa import options
from pycpa import schedulers as pycpaschedulers
from taskchain import schedulers as taskchainschedulers
from taskchain import path_analysis as taskchainpath_analysis

def run(scheduler):
    # generate an new system
    s = model.System()

    # add two resources (CPUs) to the system
    # and register the static priority preemptive scheduler
    r1 = s.bind_resource(model.Resource("R1", scheduler))

    # create and bind tasks to r1
    t11 = r1.bind_task(model.Task("T11", wcet=10, bcet=1, scheduling_parameter=6))
    t21 = r1.bind_task(model.Task("T21", wcet=2, bcet=2, scheduling_parameter=2))
    t31 = r1.bind_task(model.Task("T31", wcet=4, bcet=2, scheduling_parameter=3))

    t12 = r1.bind_task(model.Task("T12", wcet=3, bcet=1, scheduling_parameter=5))
    t22 = r1.bind_task(model.Task("T22", wcet=9, bcet=4, scheduling_parameter=4))
    t32 = r1.bind_task(model.Task("T32", wcet=5, bcet=3, scheduling_parameter=1))

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

    # print the worst case response times (WCRTs)
    print("Result:")
    for r in sorted(s.resources, key=str):
        for t in sorted(r.tasks, key=str):
            print("%s: wcrt=%d" % (t.name, task_results[t].wcrt))
            print("    b_wcrt=%s" % (task_results[t].b_wcrt_str()))

    return [task_results, [s1, s2]]

#    # print path latency for the three event
#    for n in range(1, 4):
#        best_case_latency, worst_case_latency = path_analysis.end_to_end_latency(s1, task_results, n)
#        print("stream S1 e2e latency. worst case: %d" % (worst_case_latency))
#
#    for n in range(1, 4):
#        best_case_latency, worst_case_latency = path_analysis.end_to_end_latency(s2, task_results, n)
#        print("stream S2 e2e latency. worst case: %d" % (worst_case_latency))
#
#    return task_results

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    print("\n## Using simple taskchain scheduler ##")
    [results1,paths1] = run(taskchainschedulers.SPPScheduler())
    print("\n## Using improved taskchain scheduler ##")
    [results2,paths2] = run(taskchainschedulers.ChainScheduler())

    print("\n## Comparing e2e path results##")
    for i in range(0, len(paths1)):
        [tmp, l1] = path_analysis.end_to_end_latency(paths1[i], results1)
        [tmp, l2] = taskchainpath_analysis.end_to_end_latency(paths2[i], results2)
        diff = l1-l2
        perc = float(diff) / float(l1) * 100
        print("%s: %d - %d = %d (%d%%)" % (paths1[i].name, l1, l2, diff, perc))
