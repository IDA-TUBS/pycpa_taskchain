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
from pycpa import path_analysis
from taskchain import model as tc_model
from taskchain import schedulers as tc_schedulers
from taskchain import parser

import csv
import itertools

options.parser.add_argument('file', type=str,
        help="GraphML file containing the task-chain model.")
options.parser.add_argument('--outfile', type=str,
        help="Filename of output file containing the analysis results.")
options.parser.add_argument('--single_tasks', action='store_true',
        help="Decompose into single tasks.")
options.parser.add_argument('--scheduler', type=str, default='SPPSchedulerSegments',
        help="Scheduler class to be used for the analysis.")
options.parser.add_argument('--name', type=str, required=True,
        help="Name of the analysis.")
options.parser.add_argument('--print', action='store_true',
        help="Also print analysis results to stdout.")

def write_header(contexts, name):
    if options.get_opt('outfile'):
        header = ["Path"]
        for c in contexts:
            header += [c.name]
        header += [name]

        with open(options.get_opt('outfile'), "w") as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')
            writer.writerow(header)

def write_results(contexts, results):
    if options.get_opt('print'):
        print("\nResults for priority assignment: %s" % str([c.priority for c in contexts]))

        for path, result in results.items():
            print("%s\t%s" % (path.name, result))

    if options.get_opt('outfile'):
        with open(options.get_opt('outfile'), "a") as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')

            prio_list = list()
            for c in contexts:
                prio_list += [str(c.priority)]

            for path, result in results.items():
                row = [path.name] + prio_list
                row += [result]

                writer.writerow(row)

class Experiment(object):
    def __init__(self, scheduler, resource_model, build_chains=False):
        self.scheduler = scheduler
        self.resource_model = resource_model
        self.results = dict()
        self.task_results = None
        self.build_chains = build_chains
        self.paths = list()

    def _calculate_latencies(self):
        # perform path analysis
        self.results = dict()
        for p in self.paths:
            self.results[p] = path_analysis.end_to_end_latency(p, self.task_results, 1)[1]

    def clear_results(self):
        for p in self.paths:
            self.results[p] = 0

        self.task_results = None

    def run(self, priorities):
        assert(len(priorities) >= len(m.sched_ctxs))

        i = 0
        for s in self.resource_model.sched_ctxs:
            s.priority = priorities[i]
            self.resource_model.update_scheduling_parameters(s)
            i += 1

        sys = model.System("System")
        res = sys.bind_resource(tc_model.TaskchainResource("R1", scheduler=self.scheduler))

        endpoints = set()
        if not self.paths:
            for t in self.resource_model.tasks:
                if len(self.resource_model.successors(t)) == 0:
                    endpoints.add(t)

        # then, bind model and create taskschains because it might change the taskmodel (in case of SPPSchedulerSegmentsUniform)
        res.build_from_model(self.resource_model)
        res.create_taskchains(single=not self.build_chains)

        # then, find how the previously identified endpoints map to the taskgraph now
        for ep in endpoints:
            p = self.resource_model.root_path(ep)
            self.paths.append(model.Path(p[-1].name, p))

        self.task_results = analysis.analyze_system(sys)

        self._calculate_latencies()

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    p = parser.Graphml()
    m = p.model_from_file(options.get_opt('file'))
    assert(m.check())

    schedname =  options.get_opt('scheduler')
    print("Performing taskchain analysis with %s" % schedname)
    if schedname.startswith('pycpa'):
        sched = getattr(schedulers, schedname.split('.')[-1])
    else:
        sched = getattr(tc_schedulers, schedname)

    e = Experiment(sched(), m, build_chains=not options.get_opt('single_tasks'))

    # start output file
    num_priorities = len(m.sched_ctxs)
    write_header(m.sched_ctxs, options.get_opt('name'))

    for priorities in itertools.permutations(range(1, num_priorities+1)):
        try:
            e.run(priorities)
        except analysis.NotSchedulableException as ex:
            e.clear_results()
            print(ex)

        write_results(m.sched_ctxs, e.results)
