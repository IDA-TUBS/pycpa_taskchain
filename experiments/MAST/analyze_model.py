#!/usr/bin/env python
"""
| Copyright (C) 2020 Johannes Schlatow
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

options.parser.add_argument('file', type=str,
        help="GraphML file containing the task-chain model.")
options.parser.add_argument('--single_tasks', action='store_true',
        help="Decompose into single tasks.")
options.parser.add_argument('--scheduler', type=str, default='SPPSchedulerSegments',
        help="Scheduler class to be used for the analysis.")
options.parser.add_argument('--priorities', type=int, nargs='*',
        default=list(),
        help="List of priorities used for assignment.")

def print_results(task_results, details=True):
    for t in task_results:
        print("%s: wcrt=%d" % (t, task_results[t].wcrt))
        if details:
            print("    b_wcrt=%s" % (task_results[t].b_wcrt_str()))

def analyze(m, scheduler):
    s = model.System("System")
    r = s.bind_resource(tc_model.TaskchainResource("R1", scheduler=scheduler))
    r.build_from_model(m)
    r.create_taskchains(single=options.get_opt('single_tasks'))

    return analysis.analyze_system(s)

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    p = parser.Graphml()
    m = p.model_from_file(options.get_opt('file'))
    assert(m.check())

    priorities = options.get_opt('priorities')
    if len(priorities) > 0:
        assert(len(priorities) >= len(m.sched_ctxs))
        i = 0
        for s in m.sched_ctxs: 
            s.priority = priorities[i]
            m.update_scheduling_parameters(s)
            i += 1

    schedname = options.get_opt('scheduler')
    if schedname.startswith('pycpa'):
        sched = getattr(schedulers, schedname.split('.')[-1])
    else:
        sched = getattr(tc_schedulers, schedname)
    print("Performing taskchain analysis with %s" % options.get_opt('scheduler'))
    tc_results = analyze(m, sched())
    print_results(tc_results)
