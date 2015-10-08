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
from pycpa import graph
from pycpa import options
from pycpa import path_analysis
from taskchain import model as tc_model
from taskchain import schedulers as tc_schedulers

def taskchain_test(scheduler, priorities):
    assert(len(priorities) >= 6)
    # generate an new system
    s = model.System()

    # add two resources (CPUs) to the system
    # and register the static priority preemptive scheduler
    r1 = s.bind_resource(tc_model.TaskchainResource("R1", scheduler()))

    # create and bind tasks to r1
    t11 = r1.bind_task(model.Task("T11", wcet=10, bcet=1, scheduling_parameter=priorities[0],
        synchronous_call=False))
    t12 = r1.bind_task(model.Task("T12", wcet=2, bcet=2, scheduling_parameter=priorities[1],
        synchronous_call=True))
    t13 = r1.bind_task(model.Task("T13", wcet=4, bcet=2, scheduling_parameter=priorities[2],
        synchronous_call=True))
    t14 = r1.bind_task(model.Task("T14", wcet=5, bcet=3, scheduling_parameter=priorities[3],
        synchronous_call=True))

    t21 = r1.bind_task(model.Task("T21", wcet=3, bcet=1, scheduling_parameter=priorities[4],
        synchronous_call=False))
    t22 = r1.bind_task(model.Task("T22", wcet=9, bcet=4, scheduling_parameter=priorities[5],
        synchronous_call=True))

    # specify precedence constraints
    t11.link_dependent_task(t12).link_dependent_task(t13).link_dependent_task(t14)
    t21.link_dependent_task(t22)

    # register a periodic with jitter event model for T11 and T12
    t11.in_event_model = model.PJdEventModel(P=25, J=5)
    t21.in_event_model = model.PJdEventModel(P=100, J=0)

    # register task chains as a path
    s1 = s.bind_path(model.Path("S1", [t11, t12, t13, t14]))
    s2 = s.bind_path(model.Path("S2", [t21, t22]))

    # register task chains
    c1 = r1.bind_taskchain(tc_model.Taskchain("C1", [t11, t12, t13, t14]))
    c2 = r1.bind_taskchain(tc_model.Taskchain("C2", [t21, t22]))

    # perform the analysis
    print("Performing analysis")
    task_results = analysis.analyze_system(s)

    best_case_latency1, worst_case_latency1 = path_analysis.end_to_end_latency(s1, task_results, 1)
    print("stream S1 e2e latency. best case: %d, worst case: %d" % (best_case_latency1, worst_case_latency1))
    best_case_latency2, worst_case_latency2 = path_analysis.end_to_end_latency(s2, task_results, 1)
    print("stream S2 e2e latency. best case: %d, worst case: %d" % (best_case_latency2, worst_case_latency2))

#    for t in task_results:
#        print(str(task_results[t].b_wcrt))

    return (worst_case_latency1, worst_case_latency2)

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()
    lat1, lat2 = taskchain_test(tc_schedulers.SPPSchedulerSync, [1,6,3,5,4,3])
    assert (lat1 == 34)
    assert (lat2 == 26)
    lat1, lat2 = taskchain_test(tc_schedulers.SPPSchedulerAsync, [1,6,3,5,4,3])
    assert (lat1 == 34)
    assert (lat2 == 36)
    lat1, lat2 = taskchain_test(tc_schedulers.SPPSchedulerSyncRefined, [1,6,3,5,4,3])
    assert (lat1 == 34)
    assert (lat2 == 22)
