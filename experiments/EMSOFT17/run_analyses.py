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
from pycpa import path_analysis
from taskchain import model as tc_model
from taskchain import schedulers as tc_schedulers
from taskchain import parser 

import csv
import itertools

options.parser.add_argument('--priorities', type=int, nargs='*',
        default=list(),
        help="List of priorities used for assignment.")
options.parser.add_argument('--input', type=str, required=True,
        help="Input file.")
options.parser.add_argument('--output', type=str,
        help="Write output to file.")
options.parser.add_argument('--all_priorities', action='store_true',
        help="Perform analyses for all priority assignments.")
options.parser.add_argument('--candidate_search', action='store_true',
        help="Perform candidate search.")
options.parser.add_argument('--build_chains', action='store_true',
        help="Automatically builds task chains.")
options.parser.add_argument('--run_cpa', action='store_true',
        help="Perform classic CPA.")
options.parser.add_argument('--run_sync', action='store_true',
        help="Perform analysis on synchronous independent task chains.")
options.parser.add_argument('--run_sync_refined', action='store_true',
        help="Perform refined analysis on synchronous independent task chains.")
options.parser.add_argument('--run_async', action='store_true',
        help="Perform analysis on asynchronous independent task chains.")
options.parser.add_argument('--run_new', action='store_true',
        help="Perform new task chain analysis.")
options.parser.add_argument('--add_mutex_blocking', action='store_true',
        help="Add mutex blocking to classic CPA results.")
options.parser.add_argument('--print', action='store_true',
        help="Print analysis results.")
options.parser.add_argument('--resume', action='store_true',
        help="Continue a previous run of experiments (DOES NOT CHECK THE SETTINGS).")
options.parser.add_argument('--print_differing', action='store_true',
        help="Print details of differing WCRT results.")
options.parser.add_argument('--calculate_difference', action='store_true',
        help="Calculate difference of results (only if two experiments are executed).")

def write_header(contexts, experiment_names):
    if options.get_opt('output'):
        header = ["Chain"]
        for c in contexts:
            header += [c.name]
        header += experiment_names

        if options.get_opt('calculate_difference'):
            assert(len(experiment_names) == 2)
            header.append('diff')

        if options.get_opt('resume'):
            # read file header
            with open(options.get_opt('output'), 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter='\t')

                # assert that headers are present and in correct order
                assert(len(reader.fieldnames) == len(header))
                for i in range(len(reader.fieldnames)):
                    assert(reader.fieldnames[i] == header[i])
        else:
            with open(options.get_opt('output'), "w") as csvfile:
                writer = csv.writer(csvfile, delimiter='\t')
                writer.writerow(header)

def write_results(contexts, experiments, paths):
    if options.get_opt('print'):
        print("\nResults for priority assignment: %s" % str([c.priority for c in contexts]))
        print("Path\t%s" % "\t".join([e.name for e in experiments]))

        for path in paths:
            print("%s\t%s" % (path.name, "\t".join([str(e.results[path]) for e in experiments])))

    if options.get_opt('output'):
        with open(options.get_opt('output'), "a") as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')

            prio_list = list()
            for c in contexts:
                prio_list += [str(c.priority)]

            for path in paths:
                row = [path.name] + prio_list
                for e in experiments:
                    row += [e.results[path]]

                if options.get_opt('calculate_difference'):
                    assert(len(experiments) == 2)
                    row.append(experiments[0].results[path] - experiments[1].results[path])

                writer.writerow(row)

def parse_existing_results(contexts, experiments):
    if options.get_opt('output'):
        analysed_paths = set()
        analysed_priorities = list()

        with open(options.get_opt('output'), 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')

            last_prio_list = list()
            for row in reader:
                prio_list = list()
                for c in contexts:
                    prio_list += [row[c.name]]

                analysed_paths.add(row['Chain'])
                if last_prio_list != prio_list:
                    analysed_priorities.append(prio_list)

                last_prio_list = prio_list

        return analysed_paths, analysed_priorities
    else:
        return None, None

def print_differing(experiments, tasks):
    if not options.get_opt('print_differing'):
        return

    differing = dict()
    for t in tasks:
        for e1 in experiments:
            for e2 in experiments:
                if t not in e1.task_results or t not in e2.task_results:
                    continue
                if e1.task_results[t].wcrt != e2.task_results[t].wcrt:
                    if t not in differing:
                        differing[t] = set()

                    differing[t].add(e1)
                    differing[t].add(e2)

    if len(differing) > 0:
        print("\nThe following WCRT results are differing:")

    for t in differing.keys():
        print("\nTask %s:" % t.name)
        for exp in differing[t]:
            print("[%s]\twcrt=%d\tb_wcrt=%s" % (exp.name, exp.task_results[t].wcrt, exp.task_results[t].b_wcrt_str()))
            
class Experiment(object):
    def __init__(self, name, scheduler, resource_model, build_chains=False, add_blocking=False):
        self.name = name
        self.scheduler = scheduler
        self.resource_model = resource_model
        self.results = dict()
        self.task_results = None
        self.build_chains = build_chains
        self.add_blocking = add_blocking

    def _calculate_latencies(self, paths):
        # perform path analysis
        self.results = dict()
        for p in paths:
            self.results[p] = path_analysis.end_to_end_latency(p, self.task_results, 1)[1]

    def clear_results(self, paths):
        for p in paths:
            self.results[p] = 0

        self.task_results = None

    def run(self, priorities, paths):
        assert(len(priorities) >= len(m.sched_ctxs))

        i = 0
        for s in self.resource_model.sched_ctxs: 
            s.priority = priorities[i]
            self.resource_model.update_scheduling_parameters(s)
            i += 1

        sys = model.System("System")
        r = sys.bind_resource(tc_model.TaskchainResource("R1", scheduler=self.scheduler))
        r.build_from_model(self.resource_model)

        if self.build_chains:
            for path in paths:
                r.bind_taskchain(tc_model.Taskchain(path.name, path.tasks))
        else:
            r.create_taskchains(single=True)

        self.task_results = analysis.analyze_system(sys)

        # add mutex blocking
        if self.add_blocking:
            for t in self.task_results:
                for b in self.resource_model.get_mutex_interferers(t):
                    # b is not interfering
                    if not self.scheduler.priority_cmp(b.scheduling_parameter, t.scheduling_parameter):
                        self.task_results[t].wcrt += b.wcet

        self._calculate_latencies(paths)

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    p = parser.Graphml()
    m = p.model_from_file(options.get_opt('input'))
    assert(m.check())
    tc_model.ResourceModel.write_dot([m], 'system.dot')

    if options.get_opt('build_chains'):
        # create paths
        roots = set()
        for t in m.tasks:
            if len(m.predecessors(t)) == 0:
                roots.add(t)

        # perform a DFS
        paths = list()
        for r in roots:
            for p in m.paths(r):
                paths.append(model.Path(p[-1].name, p))
    else:
        paths = [model.Path(t.name, [t]) for t in m.tasks]

    # create list of experiments
    experiments = list()
    if options.get_opt('run_cpa'):
        experiments.append(Experiment('STD', 
            scheduler=schedulers.SPPScheduler(), 
            resource_model=m, 
            build_chains=False,
            add_blocking=options.get_opt('add_mutex_blocking')))

    if options.get_opt('run_new'):
        experiments.append(Experiment('TC',
            scheduler=tc_schedulers.SPPScheduler(candidate_search=options.get_opt('candidate_search')),
            resource_model=m,
            add_blocking=False,
            build_chains=options.get_opt('build_chains')))

    if options.get_opt('run_async'):
        # check whether analysis can be applied
        for src, dsts in m.tasklinks.items():
            for dst in dsts:
                assert not m.is_strong_precedence(src, dst),\
                        "cannot apply asynchronous chain analysis to a task graph with strong precedence"

        experiments.append(Experiment('ASYNC', 
            scheduler=tc_schedulers.SPPSchedulerAsync(), 
            resource_model=m,
            add_blocking=False,
            build_chains=options.get_opt('build_chains')))

    if options.get_opt('run_sync'):
        # check whether analysis can be applied
        for src, dsts in m.tasklinks.items():
            for dst in dsts:
                assert m.is_strong_precedence(src, dst),\
                        "cannot apply synchronous chain analysis to a task graph with weak precedence"

        experiments.append(Experiment('SYNC', 
            scheduler=tc_schedulers.SPPSchedulerSync(), 
            resource_model=m,
            add_blocking=False,
            build_chains=options.get_opt('build_chains')))

    if options.get_opt('run_sync_refined'):
        # check whether analysis can be applied
        for src, dsts in m.tasklinks.items():
            for dst in dsts:
                assert m.is_strong_precedence(src, dst),\
                        "cannot apply synchronous chain analysis to a task graph with weak precedence"

        experiments.append(Experiment('SYNCREF', 
            scheduler=tc_schedulers.SPPSchedulerSyncRefined(), 
            resource_model=m,
            add_blocking=False,
            build_chains=options.get_opt('build_chains')))

    # start output file
    num_priorities = len(m.sched_ctxs)
    write_header(m.sched_ctxs, [e.name for e in experiments])

    if options.get_opt('resume'):
        # read analysed priorities and paths from existing output file
        analysed_paths, analysed_priorities = parse_existing_results(m.sched_ctxs, experiments)

        # check that we analyse the same paths
        if analysed_paths is not None:
            assert(len(analysed_paths) == len(paths))
            for p in paths:
                assert(p.name in analysed_paths)
    else:
        analysed_priorities = None

    if options.get_opt('all_priorities') or len(options.get_opt('priorities')) == 0:

        for priorities in itertools.permutations(range(1, num_priorities+1)):
            if analysed_priorities is not None:
                skip = False
                for analysed in analysed_priorities:
                    match = True
                    for i in range(len(analysed)):
                        if int(analysed[i]) != priorities[i]:
                            match = False

                    if match:
                        skip = True
                if skip:
                    print("Skipping %s" % str(priorities))
                    continue

            for e in experiments:
                try:
                    e.run(priorities, paths)
                except analysis.NotSchedulableException as ex:
                    e.clear_results(paths)
                    print(ex)

            write_results(m.sched_ctxs, experiments, paths)
            print_differing([e for e in experiments if e.task_results is not None], m.tasks)

        # TODO optionally also use itertools.product() with repeat=n and n-1, n-2, ... priorities

    else:
        priorities = options.get_opt('priorities')
        assert(not options.get_opt('all_priorities'))
        for e in experiments:
            try:
                e.run(priorities, paths)
            except analysis.NotSchedulableException as ex:
                e.clear_results(paths)
                print(ex)

        write_results(m.sched_ctxs, experiments, paths)
        print_differing(experiments, m.tasks)

