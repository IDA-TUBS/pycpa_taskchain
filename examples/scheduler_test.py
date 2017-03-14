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

def analyze(m, scheduler):
    s = model.System("System")
    r = s.bind_resource(tc_model.TaskchainResource("R1", scheduler=scheduler))
    r.build_from_model(m)
    r.create_taskchains()

    task_results = analysis.analyze_system(s)

    for t in task_results:
        print("%s WCRT: %d" % (t, task_results[t].wcrt))

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
    analyze(m, tc_schedulers.SPPScheduler())

    print("Performing standard analysis")
    analyze(m, schedulers.SPPScheduler())
