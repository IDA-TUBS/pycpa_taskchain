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
from pycpa import model
from pycpa import analysis
from taskchain import model as tc_model
from taskchain import schedulers as tc_schedulers
from taskchain import benchmark

import numpy as np
import math

options.parser.add_argument('--output', type=str, required=True,
        help="output file.")
options.parser.add_argument('--nassign', type=int, default=100,
        help="number of random priority assignment per setup")
options.parser.add_argument('--inherit', action='store_true')

class Experiment(object):
    def __init__(self, name, resource_model, scheduler):
        self.name = name
        self.scheduler = scheduler
        self.resource_model = resource_model
        self.task_results = None

    def clear_results(self, paths):
        self.task_results = None

    def run(self):
        sys = model.System("System")
        r = sys.bind_resource(tc_model.TaskchainResource("R1", scheduler=self.scheduler))
        r.build_from_model(self.resource_model)

        r.create_taskchains()
        try:
            self.task_results = analysis.analyze_system(sys)
            return (True, False)
        except analysis.NotSchedulableException as e:
            print(e)
            return (False, False)
        except RuntimeError as e:
            print(e)
            return (False, True)

def analyze_with_increasing_load(g, m):
    for load in [0.8, 0.9, 0.95, 0.98, 0.99, 1.0]:
        print(load)
        # set WCETs randomly such that they generate the desired load
        g.random_wcet(m, load=load, rel_jitter=0.1)
        print(g.calculate_load(m))

        for n in range(options.get_opt('nassign')):
            g.random_priorities(m)
            e = Experiment('random', resource_model=m, scheduler=tc_schedulers.SPPScheduler())
            print("analysing")
            schedulable, max_recur = e.run()
            g.write_result(m, result=schedulable, max_recur=max_recur)

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()
    import sys
    sys.setrecursionlimit(150)

    resume = False
    for length in [13, 11, 9, 7, 5, 3]:
        for number in [2, 3, 5, 10, 20]:
            for nesting_depth in range(0, int(math.floor(length/2))):
                for sharing_level in range(0, 4):
                    g = benchmark.Generator(length=length, number=number, nesting_depth=nesting_depth,
                            sharing_level=sharing_level, branching_level=1, inherit=options.get_opt('inherit'))
                    m = g.random_model()
                    g.random_activation(m, min_period=1000, max_period=10000, rel_jitter=0.1)
                    assert(m.check())
                    g.write_header(options.get_opt('output'), resume=resume)
                    if not resume:
                        resume = True

                    analyze_with_increasing_load(g, m)

#    m.write_dot(options.get_opt('output'))
#    g.random_wcet(m, load=0.6, rel_jitter=0.1)
