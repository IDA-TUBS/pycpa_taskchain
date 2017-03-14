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
            self.n = float('inf')

        def events(self):
            return self.n

    class StaticEventCountBound(EventCountBound):
        def __init__(self, n):
            TaskChainBusyWindow.EventCountBound.__init__(self)
            self.n = n

        def __str__(self):
            return str(self.n)

    class DependentEventCountBound(EventCountBound):
        def __init__(self, ec_bound, multiplier=1, offset=0, recursive_refresh=True):
            TaskChainBusyWindow.EventCountBound.__init__(self)
            self.ec_bound = ec_bound
            self.multiplier = multiplier
            self.offset = offset
            self.recursive_refresh = recursive_refresh

            self._calculate()

        def _calculate(self):
            self.n = self.ec_bound.events() * self.multiplier + self.offset

        def refresh(self, **kwargs):
            if self.recursive_refresh and self.ec_bound.refresh(**kwargs):
                self._calculate()
                return True

            self._calculate()
            return False

        def __str__(self):
            return '%s=%s*%d+%d' % (self.n, str(self.ec_bound), self.multiplier, self.offset)

    class BinaryEventCountBound(EventCountBound):
        def __init__(self, ec_bound, if_non_zero=None, if_zero=None):
            TaskChainBusyWindow.EventCountBound.__init__(self)
            self.ec_bound = ec_bound

            if if_zero is None:
                self.if_zero = TaskChainBusyWindow.StaticEventCountBound(float('inf'))
            else:
                assert(isinstance(if_zero, TaskChainBusyWindow.EventCountBound))
                self.if_zero = if_zero

            if if_non_zero is None:
                self.if_non_zero = TaskChainBusyWindow.StaticEventCountBound(float('inf'))
            else:
                assert(isinstance(if_non_zero, TaskChainBusyWindow.EventCountBound))
                self.if_non_zero = if_non_zero

            self._calculate()

        def _calculate(self):
            if self.ec_bound.events() == 0:
                self.n = self.if_zero.events()
            else:
                self.n = self.if_non_zero.events()

        def refresh(self, **kwargs):
            result = self.ec_bound.refresh(**kwargs)
            result = result or self.if_zero.refresh(**kwargs)
            result = result or self.if_non_zero.refresh(**kwargs)

            self._calculate()
            return result

    class ArrivalEventCountBound(EventCountBound):
        def __init__(self, eventmodel):
            TaskChainBusyWindow.EventCountBound.__init__(self)
            self.em = eventmodel

        def refresh(self, **kwargs):
            new = self.em.eta_plus(kwargs['window'])
            if new != self.n:
                self.n = new
                return True

            return False

        def __str__(self):
            return '%s(eta)' % (self.n)

    class CombinedEventCountBound(EventCountBound):
        def __init__(self, bounds=None, func=sum, recursive_refresh=True):
            TaskChainBusyWindow.EventCountBound.__init__(self)
            self.func = func
            self.recursive_refresh = recursive_refresh
            if bounds is None:
                self.bounds = set()
            else:
                self.bounds = bounds

        def _calculate(self):
            self.n = self.func([b.events() for b in self.bounds])

        def refresh(self, **kwargs):
            result = False
            if self.recursive_refresh:
                for b in self.bounds:
                    if b.refresh(**kwargs):
                        result = True

            self._calculate()

            return result

        def add_bound(self, bound):
            self.bounds.add(bound)
            self._calculate()

        def __str__(self):
            if self.func is sum:
                res = ""
                for b in self.bounds:
                    if len(res) > 0:
                        res = res + ' + '

                    res = res + '[' + str(b) + ']'

                return res
            else:
                best_b = None
                for b in self.bounds:
                    if best_b is None:
                        best_b = b
                    else:
                        best_val = best_b.events()
                        cur_val  = b.events()
                        if self.func([best_val, cur_val]) != best_val:
                            best_b = b

                return str(best_b)

    class OptimumEventCountBound(CombinedEventCountBound):
        def __init__(self, bounds=None, func=min):
            TaskChainBusyWindow.CombinedEventCountBound.__init__(self, bounds, func=func)

    class WorkloadBound(Bound):
        def __init__(self, **kwargs):
            self.value = float('inf')

        def workload(self):
            return self.value

        def __str__(self):
            return '%s' % self.value

    class SimpleWorkloadBound(WorkloadBound):
        def __init__(self, ec_bound, cet):
            TaskChainBusyWindow.WorkloadBound.__init__(self)
            self.event_count = ec_bound
            self.cet = cet

            self._calculate()

        def _calculate(self):
            self.value = self.event_count.events() * self.cet

        def refresh(self, **kwargs):
            if self.event_count.refresh(**kwargs):
                self._calculate()
                return True

            self._calculate()
            return False

        def __str__(self):
            return '%s=%s*%d' % (self.value, str(self.event_count), self.cet)

        def __repr__(self):
            return '<%s: ec_bound=%s cet=%d>' % (type(self), repr(self.event_count), self.cet)

    class StaticWorkloadBound(WorkloadBound):
        def __init__(self, workload):
            TaskChainBusyWindow.WorkloadBound.__init__(self)
            self.value = workload

        def __repr__(self):
            return '<%s: workload=%s>' % (type(self), self.value)

    class CombinedWorkloadBound(WorkloadBound):
        def __init__(self, bounds=None, func=sum):
            TaskChainBusyWindow.WorkloadBound.__init__(self)
            self.func=func
            if bounds is None:
                self.bounds = set()
            else:
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

            self._calculate()

            return result

        def add_bound(self, bound):
            self.bounds.add(bound)
            self._calculate()

        def __str__(self):
            if self.func is sum:
                res = ""
                for b in self.bounds:
                    if len(res) > 0:
                        res = res + ' + '

                    res = res + '[' + str(b) + ']'

                return res
            else:
                best_b = None
                for b in self.bounds:
                    if best_b is None:
                        best_b = b
                    else:
                        best_val = best_b.workload()
                        cur_val  = b.workload()
                        if self.func([best_val, cur_val]) != best_val:
                            best_b = b

                return str(best_b)

        def __repr__(self):
            return '<%s: func=%s of \n {%s}>' % (type(self), self.func, self.bounds)

    class OptimumWorkloadBound(CombinedWorkloadBound):
        def __init__(self, bounds=None, func=min):
            TaskChainBusyWindow.CombinedWorkloadBound.__init__(self, bounds, func=func)

        def workload(self):
            if len(self.bounds) == 0:
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
        print("refreshing for w=%d" % window)
        while True:
            modified = False
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
            self._refresh(w)

            w_new = 0
            for b in self.upper_bounds.values():
                if b.workload() == float('inf'):
                    print(b)
                assert(b.workload() != float('inf'))
                print("%d += %s" % (w_new, b.workload()))
                assert(b.workload() == b.workload())
                w_new += b.workload()
                assert(w_new == w_new)

            if w_new == w:
                return w
            elif w_new < w:
                print("%d < %d" % (w_new, w))
            else:
                print(w_new)

            assert(w_new == w_new)
            assert(w_new > w)
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

    def _build_bounds(self, bw, q):
        # fill TaskChainBusyWindow with bounds
        taskchain = bw.taskchain
        resource = taskchain.resource()

        # event count bounds per task
        task_ec_bounds = dict()
        # workload bounds per task
        self.task_wl_bounds = dict()
        task_wl_bounds = self.task_wl_bounds

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

        # tasks can only interfere as often as first task of the chain (assumption: no joins)
        for tc in resource.chains:
            chain_bound = task_ec_bounds[tc.tasks[0]]
            for t in tc.tasks[1:]:
                task_ec_bounds[t].add_bound(TaskChainBusyWindow.DependentEventCountBound(\
                        chain_bound, multiplier=1, offset=0))

        # a task can only interfere as often as its predecessor + 1
        for t in resource.model.tasks:
            predecessors = resource.model.predecessors(t, strong=False)
            predecessors.update(resource.model.predecessors(t, strong=True))
            for pred in predecessors:
                task_ec_bounds[t].add_bound(TaskChainBusyWindow.DependentEventCountBound(\
                        task_ec_bounds[pred], multiplier=1, offset=1))

        # for the chain under analysis, we can add q as an upper bound for the last chain task (FIFO assumption)
        last_chain_task = bw.taskchain.tasks[-1]
        task_ec_bounds[last_chain_task].add_bound(TaskChainBusyWindow.StaticEventCountBound(q))

        # for strong precedence: a task can only interfere as often as its successor + 1
        for t in resource.model.tasks:
            successors = resource.model.successors(t, strong=True)
            for succ in successors:
                task_ec_bounds[t].add_bound(TaskChainBusyWindow.DependentEventCountBound(\
                        task_ec_bounds[succ], multiplier=1, offset=1, recursive_refresh=False))


        # build prio->task map
        prio_map = dict()
        for t in resource.model.tasks:
            prio = t.scheduling_parameter
            if prio not in prio_map:
                prio_map[prio] = set()
            prio_map[prio].add(t)

        # build set of own scheduling contexts
        tc_contexts = set()
        for t in taskchain.tasks:
            tc_contexts.add(resource.model.allocations[t][0])

        # FIXME does it matter whether the execution context is blocking or non-blocking?

        # exclude lower priority tasks if they cannot block
        # idea: the lowest prio tasks cannot interfere (if not in the taskchain and not sharing an execution context)
        #       the second lowest prio task (not blocking or in the chain) can only interfere if a lower prio task can
        #       interfere
        lp_bounds = set()
        reverse = self.priority_cmp(1, 2)
        for p in sorted(prio_map.keys(), reverse=reverse):
            for t in prio_map[p]:
                if t not in taskchain.tasks:
                    if resource.model.allocations[t][0] not in tc_contexts:
                        if len(lp_bounds) == 0:
                            task_ec_bounds[t].add_bound(TaskChainBusyWindow.StaticEventCountBound(0))
                        else:
                            # if sum of lower priority activations is zero, this is also zero
                            task_ec_bounds[t].add_bound(TaskChainBusyWindow.BinaryEventCountBound(\
                                    TaskChainBusyWindow.CombinedEventCountBound(\
                                        bounds=lp_bounds.copy(), func=sum, recursive_refresh=False),
                                    if_zero=TaskChainBusyWindow.StaticEventCountBound(0)))

            # FIXME we must still account for same priority blocking
            # we assume same priority tasks can interfere with each other
            # but only lower priority tasks are relevant for the BinaryEventCountBound used above
            lp_bounds.update([task_ec_bounds[t] for t in prio_map[p]])

        # convert event count bounds into workload bounds using WCET
        for t, ecb in task_ec_bounds.items():
            task_wl_bounds[t] = TaskChainBusyWindow.SimpleWorkloadBound(ecb, t.wcet)

        # now we can combine the tasks' workload bounds
        for s in resource.model.sched_ctxs:
            combined = TaskChainBusyWindow.CombinedWorkloadBound(func=sum)
            assert(len(combined.bounds) == 0)
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

        self._build_bounds(bw, q)

        print("calculating b_plus(%s, q=%d)" % (task, q))
        w = bw.calculate()
#        for t, wlb in self.task_wl_bounds.items():
#            print("%s: %s" % (t, wlb))
#        for s, b in bw.upper_bounds.items():
#            print("%s: %s" % (s, b))
        return w


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
