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

options.parser.add_argument('--priorities', type=int, nargs='*',
        default=list(),
        help="List of priorities used for assignment.")
options.parser.add_argument('--candidate_search', action='store_true',
        help="Perform candidate search.")
options.parser.add_argument('--build_chains', action='store_true',
        help="Automatically builds task chains.")

def print_results(task_results, details=True):
    for t in task_results:
        print("%s: wcrt=%d" % (t, task_results[t].wcrt))
        if details:
            print("    b_wcrt=%s" % (task_results[t].b_wcrt_str()))

def analyze(m, scheduler):
    s = model.System("System")
    r = s.bind_resource(tc_model.TaskchainResource("R1", scheduler=scheduler))
    r.build_from_model(m)
    r.create_taskchains(single=not options.get_opt('build_chains'))

    return analysis.analyze_system(s)

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    p = parser.Graphml()
    m = p.model_from_file("models/test.graphml")
    assert(m.check())
    m.write_dot('test.dot')

    priorities = options.get_opt('priorities')
    if len(priorities) > 0:
        assert(len(priorities) >= len(m.sched_ctxs))
        i = 0
        for s in m.sched_ctxs: 
            s.priority = priorities[i]
            m.update_scheduling_parameters(s)
            i += 1

    print("Performing taskchain analysis")
    tc_results = analyze(m, tc_schedulers.SPPScheduler(candidate_search=options.get_opt('candidate_search')))
    print_results(tc_results)

    print("Performing standard analysis")
    std_results = analyze(m, schedulers.SPPScheduler())
    print_results(std_results)

    # compare results
    print("\nComparing results")
    print("Task: \tTC\tSTD\tdiff")
    differing = set()
    for t in tc_results:
        std_wcrt = std_results[t].wcrt
        for b in m.get_mutex_interferers(t):
            if b.scheduling_parameter > t.scheduling_parameter:
                std_wcrt += b.wcet
        diff = tc_results[t].wcrt - std_wcrt
        print("%s: \t%d\t%d\t%d" % (t.name, tc_results[t].wcrt, std_wcrt, diff))
        if diff:
            differing.add(t)

    print("\nThe following results are differing:")
    for t in differing:
        print("\nTask %s:" % t.name)
        print("[TC]\tb_wcrt=%s" % tc_results[t].b_wcrt_str())
        print("[STD]\tb_wcrt=%s" % std_results[t].b_wcrt_str())
