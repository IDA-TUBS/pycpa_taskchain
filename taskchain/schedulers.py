"""
| Copyright (C) 2015-2017 Johannes Schlatow
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Johannes Schlatow

Description
-----------

Local analysis functions (schedulers)
"""
from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

import itertools
import math
import logging

from pycpa import analysis
from pycpa import options

logger = logging.getLogger("pycpa")

EPSILON = 1e-9

# priority orderings
prio_high_wins_equal_fifo = lambda a, b : a >= b
prio_low_wins_equal_fifo = lambda a, b : a <= b
prio_high_wins_equal_domination = lambda a, b : a > b
prio_low_wins_equal_domination = lambda a, b : a < b

class SPPSchedulerSimple(analysis.Scheduler):
    """ Improved Static-Priority-Preemptive Scheduler for task chains

    Priority is stored in task.scheduling_parameter,
    by default numerically lower numbers have a higher priority

    Policy for equal priority is FCFS (i.e. max. interference).

    Computes busy window of an entire task chain.
    Implements Eq. 7 resp. Eq. 12 of Schlatow/RTAS16 paper 
    """

    def __init__(self, priority_cmp=prio_low_wins_equal_fifo, build_sets=None):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp

        self._build_sets = build_sets

    def _get_min_chain_prio(self, task):
        assert(task.scheduling_parameter != None)

        min_prio = task.scheduling_parameter
        for t in task.chain.tasks:
            if self.priority_cmp(min_prio, t.scheduling_parameter):
                min_prio = t.scheduling_parameter

        return min_prio

    def _compute_cet(self, task, q):
        wcet = 0
        for t in task.chain.tasks:
            wcet += t.wcet

        return q * wcet

    def _compute_interference(self, I, w):
        s = 0
        for t in I:
            n = t.chain.tasks[0].in_event_model.eta_plus(w)
            s += t.wcet * n

        return s

    def _compute_self_interference(self, H, w, q):
        s = 0
        for t in H:
            n = t.chain.tasks[0].in_event_model.eta_plus(w)
            n = max(n-q, 0)
            s += t.wcet * n

        return s

    def _compute_deferred_load(self, D):
        s = 0
        for t in D:
            s += t.wcet

        return s

    def b_min(self, task, q):
        bcet = 0
        for t in task.chain.tasks:
            bcet += t.bcet

        return q * bcet


    def b_plus(self, task, q, details=None, **kwargs):
        """ This corresponds to Equation ... TODO """
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        w = self._compute_cet(task, q)

        while True:
            s = 0

            [I,D,H] = self._build_sets(task)
            w_new = self._compute_cet(task, q) + \
                    self._compute_interference(I, w) + \
                    self._compute_self_interference(H, w, q) + \
                    self._compute_deferred_load(D)

            if w == w_new:
                assert(w >= q * task.wcet)
                if details is not None:
                    for t in task.chain.tasks:
                        details[str(t)+':q*WCET'] = str(q) + '*' + str(t.wcet) + '=' + str(q * t.wcet)

                    for t in I:
                        details[str(t)+":eta*WCET"]    = str(t.chain.tasks[0].in_event_model.eta_plus(w)) \
                                                          + "*" + str(t.wcet) + "=" \
                                                          + str(t.in_event_model.eta_plus(w) * t.wcet)
                    for t in H:
                        details[str(t)+":eta*WCET"]    = str(max(t.chain.tasks[0].in_event_model.eta_plus(w)-q,0)) \
                                                          + "*" + str(t.wcet) + "=" \
                                                          + str(t.in_event_model.eta_plus(w) * t.wcet)

                    for t in D:
                        details[str(t)+":WCET"]        = str(t.wcet)

                return w

            w = w_new

class SPPSchedulerSync(SPPSchedulerSimple):

    def __init__(self):
        SPPSchedulerSimple.__init__(self, build_sets=self._build_sets)

    def _build_sets(self, task):

        # compute minimum priority of the chain
        min_prio = self._get_min_chain_prio(task)

        I = set()
        D = set()
        for tc in task.resource.chains:
            if tc is task.chain:
                continue

            deferred = False
            H = set()
            for t in tc.tasks:
                assert(t.scheduling_parameter != None)
                if self.priority_cmp(t.scheduling_parameter, min_prio):
                    H.add(t)
                else:
                    deferred = True

            if deferred:
                D.update(H)
            else:
                I.update(H)

        return [I,D,set()]

class SPPSchedulerAsync(SPPSchedulerSimple):

    def __init__(self):
        SPPSchedulerSimple.__init__(self, build_sets=self._build_sets)

    def _build_sets(self, task):

        # compute minimum priority of the chain
        min_prio = self._get_min_chain_prio(task)

        I = set()
        D = set()
        H = set()
        for tc in task.resource.chains:
            if tc is task.chain:
                for t in tc.tasks:
                    if t is not tc.tasks[-1]:
                        assert(t.scheduling_parameter != None)
                        if self.priority_cmp(t.scheduling_parameter, min_prio):
                            H.add(t)
                continue

            deferred = False
            # iterate list of tasks (in sequential order in the chain)
            for t in tc.tasks:
                assert(t.scheduling_parameter != None)
                if self.priority_cmp(t.scheduling_parameter, min_prio):
                    if deferred:
                        D.add(t)
                    else:
                        I.add(t)
                else:
                    deferred = True

        return [I,D,H]

class SPPSchedulerSyncRefined(SPPSchedulerSimple):

    def __init__(self):
        SPPSchedulerSimple.__init__(self, build_sets=self._build_sets)

    def _build_sets(self, task):

        # compute minimum priority of the chain
        min_prio = self._get_min_chain_prio(task)

        I = set()
        D = set()
        for tc in task.resource.chains:
            if tc is task.chain:
                continue

            deferred = False
            H = set()
            for t in tc.tasks:
                assert(t.scheduling_parameter != None)
                if self.priority_cmp(t.scheduling_parameter, min_prio):
                    H.add(t)
                else:
                    deferred = True

            if deferred:
                # first shift task chain to the start of a deferred segment as the first task might
                # be in the middle of such a segment
                k = 0
                for t in tc.tasks:
                    k += 1
                    if t not in H:
                        shifted_list = tc.tasks[k::] + tc.tasks[:k:]
                        break

                # find the critical (i.e. longest) deferred segment
                max_cet = 0
                S = set()
                S_crit = set()
                for t in shifted_list:
                    if t not in H:
                        cur_cet = self._compute_deferred_load(S)
                        if max_cet < cur_cet:
                            max_cet = cur_cet
                            S_crit = S
                            
                        S = set()
                    else:
                        S.add(t)

                D.update(S_crit)
            else:
                I.update(H)

        return [I,D,set()]

class TaskChainBusyWindow(object):
    """ Computes a task chain busy window computation (scheduler-independent).
    """

    class Bound(object):
        def refresh(self, **kwargs):
            return False

    class EventCountBound(Bound):
        def __init__(self):
            return

        def events(self):
            return float('inf')

    class StaticEventCountBound(EventCountBound):
        def __init__(self, n):
            self.n = n
            return

        def events(self):
            return self.n

    class DependentEventCountBound(EventCountBound):
        def __init__(self, ec_bound, multiplier=1, offset=0):
            self.ec_bound = ec_bound
            self.multiplier = multiplier
            self.offset = offset

            self._calculate()

        def _calculate(self):
            self.n = self.ec_bound.events() * self.multiplier + self.offset

        def refresh(self, **kwargs):
            if self.ec_bound.refresh(**kwargs):
                self._calculate()
                return True

            return False

    class ArrivalEventCountBound(EventCountBound):
        def __init__(self, eventmodel):
            self.em = eventmodel
            self.n = float('inf')

        def refresh(self, **kwargs):
            new = self.em.eta_plus(kwargs['window'])
            if new != self.n:
                self.n = new
                return True

            return False

    class OptimumEventCountBound(EventCountBound):
        def __init__(self, bounds=set(), func=min):
            self.func = func
            self.bounds = bounds

        def _calculate(self):
            self.n = self.func([b.events() for b in self.bounds])


        def refresh(self, **kwargs):
            result = False
            for b in self.bounds:
                if b.refresh(**kwargs):
                    result = True

            if result:
                self._calculate()

            return result

        def add_bound(self, bound):
            self.bounds.add(bound)

    class WorkloadBound(Bound):
        def __init__(self, **kwargs):
            return

        def workload(self):
            return float('inf')

    class SimpleWorkloadBound(WorkloadBound):
        def __init__(self, ec_bound, cet):
            self.event_count = ec_bound
            self.cet = cet

            self._calculate()

        def _calculate(self):
            self.value = self.event_count.events() * self.cet

        def refresh(self, **kwargs):
            if self.event_count.refresh(**kwargs):
                self._calculate()
                return True

            return False

    class StaticWorkloadBound(WorkloadBound):
        def __init__(self, workload):
            self.value = workload

    class CombinedWorkloadBound(WorkloadBound):
        def __init__(self, bounds=set(), func=sum):
            self.func=func
            self.bounds = bounds

            if len(self.bounds) > 0:
                self._calculate()

        def _calculate(self):
            self.value = self.func([b.workload() for b in self.bounds])

        def refresh(self, **kwargs):
            result = False
            for b in self.bounds:
                if b.refresh(**kwargs):
                    result = True

            if result:
                self._calculate()

            return result

        def add_bound(self, bound):
            self.bounds.add(bound)
            self._calculate()

    class OptimumWorkloadBound(CombinedWorkloadBound):
        def __init__(self, bounds=set(), func=min):
            TaskChainBusyWindow.CombinedWorkloadBound.__init__(self, bounds, func=func)

        def workload(self):
            if len(self.bounds()) == 0:
                return float('inf')

            return TaskChainBusyWindow.CombinedWorkloadBound.workload(self)

    def __init__(self, taskchain, q):
        self.lower_bounds = dict()
        self.upper_bounds = dict()
        self.taskchain = taskchain
        self.q = q

        for t in self.taskchain.tasks:
            self.lower_bounds[t] = self.SimpleWorkloadBound(self.StaticEventCountBound(q), t.wcet)

    def add_interferer(self, intf):
        self.upper_bounds[intf] = self.OptimumWorkloadBound()
        self.upper_bounds[intf].add_bound(self.StaticWorkloadBound(float('inf')))

    def add_upper_bound(self, intf, bound):
        assert(isinstance(bound, self.WorkloadBound))
        self.upper_bounds[intf].add_bound(bound)

    def _refresh(self, window):
        modified = False
        while True:
            for b in self.upper_bounds.values():
                if b.refresh(window=window):
                    modified = True

            if not modified:
                break

    def calculate(self):
        w = 0
        for b in self.lower_bounds.values():
            assert(b.workload() != float('inf'))
            w += b.workload()

        while True:
            w_new = w
            self._refresh(w)

            for b in self.upper_bounds.values():
                assert(b.workload() != float('inf'))
                w_new += b.workload()

            if w_new == w:
                return w

            w = w_new

# TODO implement candidate search mechanism

class SPPScheduler(analysis.Scheduler):
    """ Improved Static-Priority-Preemptive Scheduler for task chains

    Priority is stored in task.scheduling_parameter,
    by default numerically lower numbers have a higher priority

    Policy for equal priority is FCFS (i.e. max. interference).

    Computes busy window of an entire task chain.
    """

    def __init__(self, priority_cmp=prio_low_wins_equal_fifo):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp

    def _create_busywindow(self, taskchain, q):
        bw = TaskChainBusyWindow(taskchain, q)

        resource = taskchain.resource()
        for s in resource.model.sched_ctxs:
            bw.add_interferer(s)

        return bw

    def _build_bounds(self, bw):
        # fill TaskChainBusyWindow with bounds
        taskchain = bw.taskchain
        resource = taskchain.resource()

        # event count bounds per task
        task_ec_bounds = dict()
        # workload bounds per task
        task_wl_bounds = dict()

        # lets be conservative and add an infinite upper bound
        inf = TaskChainBusyWindow.StaticEventCountBound(float('inf'))
        for t in resource.model.tasks:
            # build the minimum of any bound added later
            task_ec_bounds[t] = TaskChainBusyWindow.OptimumEventCountBound(bounds=set([inf]), func=min)

        # add event count bounds based on input event models
        for t in resource.model.tasks:
            # t is head of chain
            if t is t.chain.tasks[0]:
                task_ec_bounds[t].add_bound(TaskChainBusyWindow.ArrivalEventCountBound(t.in_event_model))

        # TODO create dependent event count bounds from precedence constraints

        # TODO exclude lower priority tasks if they cannot block
        # idea: the lowest prio tasks cannot interfere (if not in the taskchain and not sharing an execution context)
        #       the second lowest prio task (not blocking or in the chain) can only interfere if no lower prio task can
        #       interfere
        # pseudo-code for bound: DependentEventCountBound(CombinedWorkloadBound(bounds=lp_bounds), multiplier=float('inf'))

        # convert event count bounds into workload bounds using WCET
        for t, ecb in task_ec_bounds.items():
            task_wl_bounds[t] = TaskChainBusyWindow.SimpleWorkloadBound(ecb, t.wcet)

        # now we can combine the tasks' workload bounds
        for s in resource.model.sched_ctxs:
            combined = TaskChainBusyWindow.CombinedWorkloadBound(func=sum)
            for t in resource.model.scheduled_tasks(s):
                combined.add_bound(task_wl_bounds[t])

            bw.add_upper_bound(s, combined)

    def b_min(self, task, q):
        bcet = 0
        for t in task.chain.tasks:
            bcet += t.bcet

        return q * bcet

    def b_plus(self, task, q, details=None, **kwargs):
        """ This corresponds to Equation ... TODO """
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        assert hasattr(task, 'chain'), "b_plus called on the wrong task"

        taskchain = task.chain

        bw = self._create_busywindow(taskchain, q)

        self._build_bounds(bw)

        return bw.calculate()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
