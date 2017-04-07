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

from __future__ import absolute_import
from __future__ import print_function
#from __future__ import unicode_literals
from __future__ import division

import math
import logging
import copy
import warnings

import csv

from numpy import random

from pycpa import options
from pycpa import util
from pycpa import model
from . import model as tc_model

logger = logging.getLogger(__name__)

class Generator (object):

    def __init__(self, length, number, nesting_depth, sharing_level, branching_level, inherit=False):
        """ CTOR """
        self.length = length
        self.number = number
        self.nesting_depth = nesting_depth
        self.branching_level = branching_level
        self.sharing_level = sharing_level
        self.inherit = inherit

        assert(self.number % self.branching_level == 0)

    def random_model(self, name='random'):
        m = tc_model.ResourceModel(name)

        # running task index
        ti = 0
        # running exec. context index
        ei = 0
        # running sched. context index
        si = 0

        # create self.number chains
        for n in range(int(self.number / self.branching_level)):
            # randomly select the fork point
            l_fork = random.random_integers(1, self.length-1)
            # create tasks up to fork
            pred = None
            for l in range(l_fork):
                task = m.add_task(model.Task("T"+str(ti)))
                if pred is not None:
                    m.link_tasks(pred, task)

                pred = task
                ti += 1

            # create branches
            for b in range(self.branching_level):
                for l in range(self.length-l_fork):
                    task = m.add_task(model.Task("T"+str(ti)))
                    m.link_tasks(pred, task)
                    pred = task
                    ti += 1

        # now we create the allocation graph
        if self.nesting_depth == 0:
            # => we only have weak precedence
            tasks = list(m.tasks)
            random.shuffle(tasks)

            cur_context = None
            sharing_idx = 0
            while len(tasks) > 0:
                if cur_context is None:
                    sharing_idx = 0
                    cur_context = m.add_execution_context(tc_model.ExecutionContext("E"+str(ei)))
                    ei += 1

                m.assign_execution_context(tasks.pop(), cur_context, blocking=False)
                sharing_idx += 1
                if sharing_idx > self.sharing_level:
                    cur_context = None
        else:
            # we try to use strict precedence where possible
            paths = list()
            for t in m.tasks:
                if len(m.predecessors(t)) == 0:
                    paths.extend(m.paths(t))

            random.shuffle(paths)

            free_contexts = list()
            while len(paths) > 0:
                path = paths.pop()

                segments = list()
                segment = list()
                for t in path:
                    segment.append(t)
                    successors = m.successors(t)
                    if len(successors) > 1:
                        for succ in successors:
                            if m.is_strong_precedence(t, succ):
                                segments.append(segment)
                                segment = list()
                                break

                segments.append(segment)

                for segment in segments:
                    # TODO split segments into subsegments of length nesting_depth*2+1
                    assert(len(segment) >= (self.nesting_depth*2+1) and len(segment) % 2 == 1)

                    nested_contexts = list()
                    free_next = None
                    second = False

                    remaining = len(segment)
                    for t in segment:
                        # TODO skip if we already processed this segment

                        if remaining <= len(nested_contexts):
                            # release previously allocated context
                            release = True
                        elif len(nested_contexts) > 0 and remaining % 2 == 1 and not second:
                            release = (random.random_integers(0, 1) == 1)
                        else:
                            release = False

                        if second:
                            second = False

                        free_this = free_next

                        if release:
                            ctx = nested_contexts.pop()
                            m.assign_execution_context(t, ctx, blocking=False)

                            if len(m.allocating_tasks(ctx, only_released=True)) <= self.sharing_level:
                                free_contexts.append(ctx)
                        else:

                            if len(free_contexts) <= 1:
                                choose_free = False
                            elif len(free_contexts) < len(paths):
                                # randomly choose new context or existing one
                                choose_free = (random.random_integers(0, 1) == 1)
                            else:
                                # always choose existing context
                                choose_free = True

                            if choose_free:
                                idx = random.random_integers(0, len(free_contexts)-1)
                                ctx = free_contexts.pop(idx)
                            else:
                                ctx = m.add_execution_context(tc_model.ExecutionContext("E"+str(ei)))
                                ei += 1
                        
                            if remaining > 2 and len(nested_contexts) < self.nesting_depth:
                                nested_contexts.append(ctx)
                                nested = True
                                second = True
                            else:
                                nested = False

                            m.assign_execution_context(t, ctx, blocking=nested)
                            if not nested and len(m.allocating_tasks(ctx, only_released=True)) <= self.sharing_level:
                                free_next = ctx

                        if free_this is not None:
                            free_contexts.append(free_this)

                        for ctx in nested_contexts:
                            m.assign_execution_context(t, ctx, blocking=True)

                        remaining -= 1

        # now we need to add scheduling contexts
        if self.inherit:
            # create scheduling context for every strict precedence segment
            for t in m.tasks:
                if t not in m.mappings:
                    # create new scheduling context and map all strong successors/predecessors
                    ctx = m.add_scheduling_context(tc_model.SchedulingContext("S"+str(si)))
                    si += 1
                    m.assign_scheduling_context(t, ctx)
                    for pred in m.predecessors(t, only_strong=True, recursive=True):
                        m.assign_scheduling_context(pred, ctx)
                    for suc in m.successors(t, only_strong=True, recursive=True):
                        m.assign_scheduling_context(suc, ctx)
        else:
            # create scheduling context for every execution context
            for t in m.tasks:
                if t not in m.mappings:
                    # do we release a context
                    create_new = False
                    assign_to = set()
                    ctx = None
                    for e, blocking in m.allocations[t].items():
                        if not blocking:
                            # does our predecessor not allocate this context
                            preds = m.predecessors(t)
                            if len(preds) == 0:
                                create_new = True
                                break
                            else:
                                pred = preds.pop()
                                if e not in m.allocations[pred] or not m.allocations[pred]:
                                    # we are the only task in the segment -> create new context
                                    create_new = True
                                    break
                                else:
                                    # find predecessor with the same execution contexts
                                    for pred in m.predecessors(t, recursive=True, only_strong=True):
                                        e1 = set(m.allocations[pred].keys())
                                        e2 = set(m.allocations[t].keys())
                                        if len(e1 & e2) == len(e1):
                                            if pred in m.mappings:
                                                ctx = m.mappings[pred]
                                            else:
                                                assign_to.add(pred)

                                    if ctx is None:
                                        create_new = True

                    if create_new:
                        ctx = m.add_scheduling_context(tc_model.SchedulingContext("S"+str(si)))
                        si += 1

                    if ctx is not None:
                        m.assign_scheduling_context(t, ctx)
                        for pred in assign_to:
                            m.assign_scheduling_context(pred, ctx)

        return m

    def random_activation(self, m, min_period, max_period, rel_jitter, period_quantum=10):
        for t in m.tasks:
            if len(m.predecessors(t)) == 0:
                P = int(math.floor(random.random_integers(min_period/period_quantum, max_period/period_quantum) * period_quantum))
                t.in_event_model = model.PJdEventModel(P=P, J=int(math.floor(P*rel_jitter)))

    def random_wcet(self, m, load, rel_jitter):
        # split load equally to chains
        trees = list()
        for t in m.tasks:
            if len(m.predecessors(t)) == 0:
                trees.append([t] + list(m.successors(t, recursive=True)))

        path_load = float(load) / float(len(trees))
        for path in trees:
            period = float(path[0].in_event_model.delta_min(1000)) / float(1000)
            time = period * path_load
            actual_time = 0
            # equally distribute wcets
            for t in path:
                t.wcet = math.floor(time/len(path))
                t.bcet = max(1, math.floor(t.wcet*rel_jitter))
                actual_time += t.wcet

            path[0].wcet = math.floor(path[0].wcet + time - actual_time)

    def random_priorities(self, m):
        # just throw in priorities uniformly at random
        prios = random.permutation(len(m.sched_ctxs))
        for i in range(len(m.sched_ctxs)):
            m.sched_ctxs[i].priority = prios[i]
            m.update_scheduling_parameters(m.sched_ctxs[i])

    def calculate_load(self, m):
        trees = list()
        for t in m.tasks:
            if len(m.predecessors(t)) == 0:
                trees.append([t] + list(m.successors(t, recursive=True)))

        load = 0.0
        for tree in trees:
            em = tree[0].in_event_model
            cet = 0.0
            for t in tree:
                cet += float(t.wcet)

            load += em.load(1000) * cet

        return int(math.ceil(load * 100))

    def write_header(self, filename, resume=False):
        self.output = filename

        header = ["Length", "Number", "Nesting", "Sharing", "Branching", "Load", "Inherit", "Schedulable", "MaxRecur"]

        if resume:
            # read file header
            with open(filename, 'r') as csvfile:
                reader = csv.DictReader(csvfile, delimiter='\t')

                # assert that headers are present and in correct order
                assert(len(reader.fieldnames) == len(header))
                for i in range(len(reader.fieldnames)):
                    assert(reader.fieldnames[i] == header[i])
        else:
            with open(filename, "w") as csvfile:
                writer = csv.writer(csvfile, delimiter='\t')
                writer.writerow(header)

    def write_result(self, m, result, max_recur):
        with open(self.output, "a") as csvfile:
            writer = csv.writer(csvfile, delimiter='\t')

            row = [self.length,
                    self.number,
                    self.nesting_depth,
                    self.sharing_level,
                    self.branching_level,
                    self.calculate_load(m),
                    self.inherit,
                    result,
                    max_recur]

            writer.writerow(row)


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
