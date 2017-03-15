#!/usr/bin/env python
"""
| Copyright (C) 2017 Johannes Schlatow
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Johannes Schlatow

Description
-----------

"""

from pycpa import options
from pycpa import analysis
from pycpa import model
from pycpa import schedulers
from taskchain import model as tc_model
from taskchain import schedulers as tc_schedulers
from taskchain import parser 

def print_results(task_results, details=True):
    for t in task_results:
        print("%s: wcrt=%d" % (t, task_results[t].wcrt))
        if details:
            print("    b_wcrt=%s" % (task_results[t].b_wcrt_str()))

def analyze(m, scheduler):
    s = model.System("System")
    r = s.bind_resource(tc_model.TaskchainResource("R1", scheduler=scheduler))
    r.build_from_model(m)
    r.create_taskchains(single=True)

    return analysis.analyze_system(s)

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    p = parser.Graphml()
    m = p.model_from_file("test.graphml")
    assert(m.check())
    m.write_dot('test.dot')

    priorities = [1, 2, 3, 4, 5, 6, 7, 8, 9]
    i = 0
    for s in m.sched_ctxs: 
        s.priority = priorities[i]
        m.update_scheduling_parameters(s)
        i += 1

    print("Performing taskchain analysis")
    tc_results = analyze(m, tc_schedulers.SPPScheduler(candidate_search=True))
    print_results(tc_results)

    print("Performing standard analysis")
    std_results = analyze(m, schedulers.SPPScheduler())
    print_results(std_results)

    # compare results
    print("Comparing results")
    print("Task: \tTC\tSTD\tdiff")
    for t in tc_results:
        std_wcrt = std_results[t].wcrt
        for b in m.get_mutex_interferers(t):
            if b.scheduling_parameter > t.scheduling_parameter:
                std_wcrt += b.wcet
        print("%s: \t%d\t%d\t%d" % (t.name, tc_results[t].wcrt, std_wcrt, tc_results[t].wcrt - std_wcrt))
