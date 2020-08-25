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
import copy
import time

from multiprocessing import Process

options.parser.add_argument('folder', type=str,
        help="Folder containing GraphML files and settings.csv.")
options.parser.add_argument('--outpath', type=str, required=True,
        help="Output path for creating schedulability.csv and latency.csv.")
options.parser.add_argument('--single_tasks', action='store_true',
        help="Decompose into single tasks.")
options.parser.add_argument('--resume', type=int, default=0,
        help="Start at given index.")
options.parser.add_argument('--scheduler', type=str, default='SPPSchedulerSegments',
        help="Scheduler class to be used for the analysis.")
options.parser.add_argument('--name', type=str,
        help="Name of the analysis.")

def parse_settings(filename):
    result = list()
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter='\t')
        for row in reader:
            row['filename'] = 'model-%s.graphml' % row['Index']
            result.append(row)

    return result

class LatencyResults():
    def __init__(self, filename, name, fieldnames, resume=False):
        self.filename   = filename
        self.name       = name
        self.fieldnames = fieldnames
        self.fieldnames += ['Path', self.name]

        if not resume:
            self.write_header()

    def write_header(self):
        with open(self.filename, "w") as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')
            writer.writerow(self.fieldnames)

    def write_results(self, setting, results):
        with open(self.filename, "a") as csvfile:
            writer = csv.DictWriter(csvfile, delimiter='\t', fieldnames=self.fieldnames)
            row = copy.copy(setting)

            for path, result in results.items():
                row['Path']    = path.name
                row[self.name] = result

            writer.writerow(row)


class SchedulabilityResults():
    def __init__(self, filename, name, fieldnames, resume=False):
        self.filename   = filename
        self.name       = name
        self.fieldnames = fieldnames
        self.fieldnames += [self.name, 'Time']

        if not resume:
            self.write_header()

    def write_header(self):
        with open(self.filename, "w") as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')
            writer.writerow(self.fieldnames)

    def write_results(self, setting, result, time):
        with open(self.filename, "a") as csvfile:
            writer = csv.DictWriter(csvfile, delimiter='\t', fieldnames=self.fieldnames)
            row = copy.copy(setting)
            row[self.name] = result
            row['Time'] = time

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

    def run(self):
        sys = model.System("System")
        r = sys.bind_resource(tc_model.TaskchainResource("R1", scheduler=self.scheduler))
        r.build_from_model(self.resource_model)
        r.create_taskchains(single=not self.build_chains)

        if not self.paths:
            roots = set()
            for t in self.resource_model.tasks:
                if len(self.resource_model.predecessors(t)) == 0:
                    roots.add(t)

            # perform a DFS
            for r in roots:
                for p in self.resource_model.paths(r):
                    self.paths.append(model.Path(p[-1].name, p))

        # TODO do we need to check that chains reflect paths?

        start = time.process_time()
        try:
            self.task_results = analysis.analyze_system(sys)
            self._calculate_latencies()
            state = "SCHED"
        except analysis.NotSchedulableException as e:
            print(e)
            state = "UNSCHED"
        except analysis.TimeoutException as e:
            print(e)
            state = "TIMEOUT"
        except RuntimeError as e:
            print(e)
            state = "MAXRECUR"

        analysistime = time.process_time() - start
        return state, analysistime


if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    # set recursion limit because SPPScheduler might go into deep recursions
    import sys
    sys.setrecursionlimit(200)

    resume = options.get_opt('resume')

    p = parser.Graphml()

    settings = parse_settings('%s/settings.csv' % options.get_opt('folder'))
    schedname =  options.get_opt('scheduler')

    latres   = LatencyResults(filename='%s/latency.csv' % options.get_opt('outpath'),
                              name=options.get_opt('name'),
                              fieldnames=sorted(settings[0].keys()),
                              resume=resume)
    schedres = SchedulabilityResults(filename='%s/schedulability.csv' % options.get_opt('outpath'),
                                     name=options.get_opt('name'),
                                     fieldnames=sorted(settings[0].keys()),
                                     resume=resume)

    print("Start analysing %d models." % len(settings))
    for s in settings:
        if resume and int(s['Index']) < resume:
            continue

        m = p.model_from_file('%s/%s' % (options.get_opt('folder'), s['filename']))

        if schedname.startswith('pycpa'):
            sched = getattr(schedulers, schedname.split('.')[-1])
        else:
            sched = getattr(tc_schedulers, schedname)


        relaxed = False
        if schedname == 'SPPSchedulerSegmentsUniform' or schedname.startswith('pycpa'):
            inserted = m.relax_model()
            if inserted > 0:
                relaxed = True
                assert m.check()
                tc_model.ResourceModel.write_dot([m], 'system.dot')

        print("Performing taskchain analysis of %s%s with %s" % ('relaxed ' if relaxed else '', s['filename'], schedname))
        e = Experiment(sched(), m, build_chains=not options.get_opt('single_tasks'))

        res, analysistime = e.run()
        schedres.write_results(s, res, analysistime)
        if res == 'SCHED':
            latres.write_results(s, e.results)
