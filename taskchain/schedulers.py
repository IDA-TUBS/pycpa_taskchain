"""
| Copyright (C) 2015-2020 Johannes Schlatow
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
from pycpa import model

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
    Builds the basis for Eq. 7, Eq. 10 and Eq. 12 of [RTAS16].
    """

    def __init__(self, priority_cmp=prio_low_wins_equal_fifo, build_sets=None):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp

        self._build_sets = build_sets

    def _get_min_chain_prio(self, taskchain):
        min_prio = taskchain.tasks[0].scheduling_parameter
        for t in taskchain.tasks:
            if self.priority_cmp(min_prio, t.scheduling_parameter):
                min_prio = t.scheduling_parameter

        return min_prio

    def _compute_cet(self, taskchain, q):
        wcet = 0
        for t in taskchain.tasks:
            wcet += t.wcet

        return q * wcet

    def _compute_interference(self, taskchain, I, w):
        s = 0
        for t in I:
            for tc in taskchain.tasks[0].resource.chains:
                if t in tc.tasks:
                    n = tc.tasks[0].in_event_model.eta_plus(w)
                    s += t.wcet * n

        return s

    def _compute_self_interference(self, taskchain, H, w, q):
        s = 0
        for t in H:
            n = taskchain.tasks[0].in_event_model.eta_plus(w)
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
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        assert hasattr(task, 'chain'), "b_plus called on the wrong task"

        taskchain = task.chain

        w = self._compute_cet(taskchain, q)

        while True:
            [I,D,H] = self._build_sets(taskchain)
            w_new = self._compute_cet(taskchain, q) + \
                    self._compute_interference(taskchain, I, w) + \
                    self._compute_self_interference(taskchain, H, w, q) + \
                    self._compute_deferred_load(D)

            if w == w_new:
                assert(w >= q * task.wcet)
                if details is not None:
                    for t in taskchain.tasks:
                        details[str(t)+':q*WCET'] = str(q) + '*' + str(t.wcet) + '=' + str(q * t.wcet)

                    for t in I:
                        details[str(t)+":eta*WCET"]    = str(taskchain.tasks[0].in_event_model.eta_plus(w)) \
                                                          + "*" + str(t.wcet) + "=" \
                                                          + str(taskchain.tasks[0].in_event_model.eta_plus(w) * t.wcet)
                    for t in H:
                        details[str(t)+":eta*WCET"]    = str(max(taskchain.tasks[0].in_event_model.eta_plus(w)-q,0)) \
                                                          + "*" + str(t.wcet) + "=" \
                                                          + str(max(taskchain.tasks[0].in_event_model.eta_plus(w)-q,0) * t.wcet)

                    for t in D:
                        details[str(t)+":WCET"]        = str(t.wcet)

                return w

            w = w_new

class SPPSchedulerSync(SPPSchedulerSimple):

    def __init__(self):
        SPPSchedulerSimple.__init__(self, build_sets=self._build_sets)

    def _build_sets(self, taskchain):
        """ This implements Eq. 7 from [RTAS16]"""

        # compute minimum priority of the chain
        min_prio = self._get_min_chain_prio(taskchain)

        I = set()
        D = set()
        for tc in taskchain.tasks[0].resource.chains:
            if tc is taskchain:
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

    def _build_sets(self, taskchain):
        """ This implements Eq. 12 from [RTAS16]"""

        # compute minimum priority of the chain
        min_prio = self._get_min_chain_prio(taskchain)

        I = set()
        D = set()
        H = set()
        for tc in taskchain.tasks[0].resource.chains:
            if tc is taskchain:
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

    def _build_sets(self, taskchain):
        """ This implements Eq. 10 from [RTAS16]"""

        # compute minimum priority of the chain
        min_prio = self._get_min_chain_prio(taskchain)

        I = set()
        D = set()
        for tc in taskchain.tasks[0].resource.chains:
            if tc is taskchain:
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
    """ Computes a task chain busy window computation (scheduler-independent) as presented in [EMSOFT17].
    """

    class Bound(object):
        def refresh(self, **kwargs):
            return False

    class EventCountBound(Bound):
        def __init__(self):
            self.n = float('inf')

        def calculate(self):
            old_value = self.n
            self._calculate()
            if self.n != old_value:
                return True

            return False

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

            return self.calculate()

        def __str__(self):
            if self.recursive_refresh:
                return '%s*%d+%d=%s' % (str(self.ec_bound), self.multiplier, self.offset, self.n)
            else:
                return 'X*%d+%d=%s' % (self.multiplier, self.offset, self.n)

    class BinaryEventCountBound(EventCountBound):
        def __init__(self, ec_bound, if_non_zero=None, if_zero=None, recursive_refresh=True):
            TaskChainBusyWindow.EventCountBound.__init__(self)
            self.ec_bound = ec_bound
            self.recursive_refresh = recursive_refresh

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
            if self.recursive_refresh:
                result = self.ec_bound.refresh(**kwargs)
                result = self.if_zero.refresh(**kwargs) or result
                result = self.if_non_zero.refresh(**kwargs) or result

                return self.calculate() or result
            else:
                return self.calculate()

        def __str__(self):
            if self.ec_bound.events() == 0:
                return str(self.if_zero)
            else:
                return str(self.if_non_zero)

    class ArrivalEventCountBound(EventCountBound):
        def __init__(self, eventmodel):
            TaskChainBusyWindow.EventCountBound.__init__(self)
            self.em = eventmodel

        def refresh(self, **kwargs):
            new = self.em.eta_plus(kwargs['window'])
            if new != self.n:
                assert(new >= 1)
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

            return self.calculate() or result

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

    class MinMaxEventCountBound(CombinedEventCountBound):
        def __init__(self, lower_bounds=None, upper_bounds=None):
            TaskChainBusyWindow.CombinedEventCountBound.__init__(self, lower_bounds, func=max)

            self.upper_bound = TaskChainBusyWindow.CombinedEventCountBound(upper_bounds, func=min)
            self.add_bound(self.upper_bound)

        def add_upper_bound(self, bound):
            self.upper_bound.add_bound(bound)

        def add_lower_bound(self, bound):
            self.add_bound(bound)

    class WorkloadBound(Bound):
        def __init__(self, **kwargs):
            self.value = float('inf')

        def workload(self):
            return self.value

        def calculate(self):
            old_value = self.value
            self._calculate()
            if old_value != self.value:
                return True

            return False

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

            return self.calculate()

        def __str__(self):
            return '%s*%d=%s' % (str(self.event_count), self.cet, self.value)

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

            return self.calculate() or result

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
        self.lower_ec_bounds = dict()
        self.upper_bounds = dict()
        self.taskchain = taskchain
        self.q = q

        for t in self.taskchain.tasks:
            self.lower_ec_bounds[t] = self.StaticEventCountBound(q)
            self.lower_bounds[t] = self.SimpleWorkloadBound(self.lower_ec_bounds[t], t.wcet)

    def add_interferer(self, intf):
        self.upper_bounds[intf] = self.OptimumWorkloadBound()
        self.upper_bounds[intf].add_bound(self.StaticWorkloadBound(float('inf')))

    def add_upper_bound(self, intf, bound):
        assert(isinstance(bound, self.WorkloadBound))
        self.upper_bounds[intf].add_bound(bound)

    def _refresh(self, window):
        modified = False
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
                assert(b.workload() != float('inf'))
                assert(b.workload() == b.workload())
                w_new += b.workload()
                assert(w_new == w_new)

            if w_new == w:
                return w

            assert(w_new == w_new)
            if w_new <= w:
                print("%d <= %d" % (w_new, w))
            assert(w_new > w)
            w = w_new

class CandidateSearch(object):

    class SelectableEventCountBound(TaskChainBusyWindow.EventCountBound):
        def __init__(self, if_selected=float('inf'), if_not_selected=float('inf')):
            TaskChainBusyWindow.EventCountBound.__init__(self)

            if isinstance(if_selected, TaskChainBusyWindow.EventCountBound):
                self.if_selected = if_selected
            else:
                self.if_selected = TaskChainBusyWindow.StaticEventCountBound(if_selected)

            if isinstance(if_not_selected, TaskChainBusyWindow.EventCountBound):
                self.if_not_selected = if_not_selected
            else:
                self.if_not_selected = TaskChainBusyWindow.StaticEventCountBound(if_not_selected)

            self.selected = True

            self._calculate()

        def _calculate(self):
            if self.selected:
                self.n = self.if_selected.events()
            else:
                self.n = self.if_not_selected.events()

        def refresh(self, **kwargs):
            if self.selected:
                result = self.if_selected.refresh(**kwargs)
            else:
                result = self.if_not_selected.refresh(**kwargs)

            return self.calculate() or result

        def select(self):
            self.selected = True

        def unselect(self):
            self.selected = False

        def __str__(self):
            if self.selected:
                return str(self.if_selected)
            else:
                return str(self.if_not_selected)

    class AlternativeBounds(object):

        def __init__(self):
            self.bounds = list()
            self.selection = 0

        def add_bound(self, bound):
            assert(isinstance(bound, TaskChainBusyWindow.Bound))
            self.bounds.append(bound)

        def choices(self):
            return len(self.bounds)

        def choose(self, choice):
            assert(choice < len(self.bounds))
            self.selection = choice

            for i in range(len(self.bounds)):
                if i == self.selection:
                    self.bounds[i].select()
                else:
                    self.bounds[i].unselect()

            for b in self.bounds:
                b.refresh()

    def __init__(self, busy_window, func=max):
        assert(isinstance(busy_window, TaskChainBusyWindow))
        self.busy_window = busy_window
        self.func = func

        self.alternatives = list()

    def add_alternative(self, alternative):
        assert(isinstance(alternative, CandidateSearch.AlternativeBounds))
        self.alternatives.append(alternative)

    def search(self):
        if len(self.alternatives) == 0:
            return self.busy_window.calculate()

        possibilities = list()
        for alt in self.alternatives:
            possibilities.append(range(alt.choices()))

        value = None
        for selection in itertools.product(*possibilities):
            for i in range(len(selection)):
                self.alternatives[i].choose(selection[i])

            cur_value = self.busy_window.calculate()
            if value is None:
                value = cur_value
            else:
                value = self.func(value, cur_value)

        return value

class SPPScheduler(analysis.Scheduler):
    """ Improved Static-Priority-Preemptive Scheduler for task chains

    Priority is stored in task.scheduling_parameter,
    by default numerically lower numbers have a higher priority

    Policy for equal priority is FCFS (i.e. max. interference).

    Computes busy window of an entire task chain as presented in [EMSOFT17].
    """

    def __init__(self, priority_cmp=prio_low_wins_equal_fifo, candidate_search=False, helping=False):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp

        self.perform_candidate_search = candidate_search
        self.helping = helping
        self.candidates = None
        self.independent_tasks = set()

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
        # refers to Eq. 9 in [EMSOFT17]
        inf = TaskChainBusyWindow.StaticEventCountBound(float('inf'))
        for t in resource.model.tasks:
            # build the minimum of any bound added later
            task_ec_bounds[t] = TaskChainBusyWindow.MinMaxEventCountBound(upper_bounds=set([inf]))
            if t in bw.lower_ec_bounds:
                # if there is a lower bound (i.e. q-events for the chain's tasks), add min/max bound
                # refers to Eq. 8 in [EMSOFT17]
                task_ec_bounds[t].add_lower_bound(bw.lower_ec_bounds[t])

        # add event count bounds based on input event models of chains
        # refers to Eq. 10 in [EMSOFT17]
        for c in resource.chains:
            for t in c.tasks:
                task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.ArrivalEventCountBound(c.tasks[0].in_event_model))

        # a task can only interfere once if there is a lower-priority or strong predecessor that cannot execute at all
        # part of Eq. 13 in [EMSOFT17]
        for t in resource.model.tasks:
            predecessors = resource.model.predecessors(t, only_strong=True, recursive=True)
            for pred in predecessors:
                task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.BinaryEventCountBound(\
                        task_ec_bounds[pred], if_zero=TaskChainBusyWindow.StaticEventCountBound(1)))

            predecessors = resource.model.predecessors(t, only_strong=False, recursive=True)
            for pred in predecessors:
                if self.priority_cmp(t.scheduling_parameter, pred.scheduling_parameter):
                    task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.BinaryEventCountBound(\
                            task_ec_bounds[pred], if_zero=TaskChainBusyWindow.StaticEventCountBound(1)))

        # for the chain under analysis, we can add q as an upper bound for the last chain task (FIFO assumption) and any strong predecessor
        # Eq. 11  in [EMSOFT17]
        last_chain_task = bw.taskchain.tasks[-1]
        task_ec_bounds[last_chain_task].add_upper_bound(TaskChainBusyWindow.StaticEventCountBound(q))

        # Eq. 12 in [EMSOFT17]
        for t in resource.model.predecessors(last_chain_task, recursive=True, only_strong=True):
            if t in bw.taskchain.tasks:
                task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.StaticEventCountBound(q))

#        # for the chain under analysis, any task can only execute as often as its predecessor
#        # (and vice versa for strong precedence)
#        for t in bw.taskchain.tasks:
#            for succ in resource.model.successors(t, recursive=False):
#                if succ in bw.taskchain.tasks:
#                    task_ec_bounds[succ].add_upper_bound(TaskChainBusyWindow.DependentEventCountBound(task_ec_bounds[t],
#                        offset=0, multiplier=1, recursive_refresh=True))
#                    if resource.model.is_strong_precedence(t, succ):
#                        task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.DependentEventCountBound(task_ec_bounds[succ],
#                            offset=0, multiplier=1, recursive_refresh=False))


        # for strong precedence: a task can only interfere once if there is any successor that cannot execute at all
        # can be applied recursively to all strong successors
        # part of Eq. 13 in [EMSOFT17]
        for t in resource.model.tasks:
            successors = resource.model.successors(t, recursive=True, only_strong=True)
            for succ in successors:
                task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.BinaryEventCountBound(\
                        task_ec_bounds[succ], if_zero=TaskChainBusyWindow.StaticEventCountBound(1), recursive_refresh=False))


        # build prio->task map
        prio_map = dict()
        for t in resource.model.tasks:
            prio = t.scheduling_parameter
            if prio not in prio_map:
                prio_map[prio] = set()
            prio_map[prio].add(t)

        # build set of own execution contexts
        tc_contexts = set()
        for t in taskchain.tasks:
            tc_contexts.update(resource.model.allocations[t].keys())

        # build set of higher priority tasks
        hp_tasks = set()
        for t in resource.model.tasks - set(taskchain.tasks):
            for t2 in taskchain.tasks:
                if self.priority_cmp(t.scheduling_parameter, t2.scheduling_parameter):
                    hp_tasks.add(t)
                    break

        # build set of lp tasks
        lp_tasks = set()
        reverse = self.priority_cmp(1, 2)
        for p in sorted(prio_map.keys(), reverse=reverse):
            # can priority interfere?
            interferes = False
            for t in taskchain.tasks:
                if self.priority_cmp(p, t.scheduling_parameter):
                    interferes = True
                    break

            if interferes:
                break

            lp_tasks.update(prio_map[p])

        # build set of possible blockers
        # Eq. 12 in [EMSOFT17]
        possible_lp_blockers = set()
        cur_len = -1
        while cur_len < len(possible_lp_blockers):
            cur_len = len(possible_lp_blockers)

            for t in lp_tasks - possible_lp_blockers:
                if t not in taskchain.tasks:

                    blocking = False
                    for e in tc_contexts:
                        if e in resource.model.allocations[t]:
                            blocking = True
                            break

                    if not blocking:
                        for hp in hp_tasks:
                            if t not in resource.model.predecessors(hp, recursive=True) and t not in resource.model.successors(hp, recursive=True):
                                if len(set(resource.model.allocations[t].keys()) & set(resource.model.allocations[hp].keys())) > 0:
                                    blocking = True
                                    break

                    if not blocking:
                        for lp in possible_lp_blockers:
                            if t not in resource.model.predecessors(lp, only_strong=True, recursive=True) and t not in resource.model.successors(lp, only_strong=True, recursive=True):
                                if len(set(resource.model.allocations[t].keys()) & set(resource.model.allocations[lp].keys())) > 0:
                                    blocking = True
                                    break

                    if blocking:
                        # add blocker
                        possible_lp_blockers.add(t)

        # exclude lower priority tasks if they cannot block
        # (a scheduling context cannot execute if its on a lower priority and not blocking)
        # idea: a lower prio task can only interfere if an even lower prio task can interfere
        #       otherwise its scheduling context will never be scheduled
        # Eq. 15 in [EMSOFT17]

        self.independent_tasks = lp_tasks - possible_lp_blockers

        lp_bounds = set()
        reverse = self.priority_cmp(1, 2)
        for p in sorted(prio_map.keys(), reverse=reverse):
            # can priority interfere?
            interferes = False
            for t in taskchain.tasks:
                if self.priority_cmp(p, t.scheduling_parameter):
                    interferes = True
                    break

            if interferes:
                break

            for t in prio_map[p]:
                if t not in possible_lp_blockers:
                    # TODO if we apply helping/donation, we can always apply the StaticEventCount(0)
                    if len(lp_bounds) == 0 or self.helping:
                        self.independent_tasks.add(t)
                        task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.StaticEventCountBound(0))
                    else:
                        # TODO we might also add t to self.independent_tasks (are there corner cases)
                        # if sum of lower priority activations is zero, this is also zero
                        task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.BinaryEventCountBound(\
                                TaskChainBusyWindow.CombinedEventCountBound(\
                                    bounds=lp_bounds.copy(), func=sum, recursive_refresh=False),
                                if_zero=TaskChainBusyWindow.StaticEventCountBound(0)))

            # we assume same priority tasks can interfere with each other
            # but only lower priority tasks are relevant for the BinaryEventCountBound used above
            lp_bounds.update([task_ec_bounds[t] for t in prio_map[p]])

        # FIXME candidate search between mutual exclusive blockers
        #   TODO consider mutual exclusive (circular) segments
        if self.candidates is not None:
            raise Exception("not imlemented")
            for ctx in tc_contexts:
                # for each execution context, we only need to account for one blocker
                alternatives = CandidateSearch.AlternativeBounds()
                for t in possible_lp_blockers:
                    # find lower priority tasks that release this execution context
                    if ctx in resource.model.allocations[t] and resource.model.allocations[t][ctx] == False:
                        segment = resource.model.get_blocking_segment(t, ctx)
                        bound = CandidateSearch.SelectableEventCountBound(if_not_selected=0)

                        chain_segment = False
                        for ti in segment:
                            if ti in taskchain.tasks:
                                chain_segment = True
                                break

                        if not chain_segment:
                            for ti in segment:
                                task_ec_bounds[ti].add_upper_bound(bound)

                            alternatives.add_bound(bound)

                if alternatives.choices() > 1:
                    self.candidates.add_alternative(alternatives)

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
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        assert hasattr(task, 'chain'), "b_plus called on the wrong task"

        taskchain = task.chain

        bw = self._create_busywindow(taskchain, q)

        if self.perform_candidate_search:
            self.candidates = CandidateSearch(bw)

        self._build_bounds(bw, q)

        if self.candidates is not None:
            w = self.candidates.search()
        else:
            w = bw.calculate()

        if details is not None:
            for t, wlb in self.task_wl_bounds.items():
                details[str(t)] = str(wlb)

            details['dependencies'] = "[%s]" % ','.join([t.name for t in taskchain.resource().model.tasks - self.independent_tasks])

        return w


class SPPSchedulerSegmentsBase(analysis.Scheduler):
    """ Static-Priority-Preemptive Scheduler for task chains with segment logic.

    Priority is stored in task.scheduling_parameter,
    by default numerically lower numbers have a higher priority

    Policy for equal priority is FCFS (i.e. max. interference).

    Computes busy window of an entire task chain as presented in TODO.
    Builds the basis for SPPSchedulerSegmentsUniform, SPPSchedulerSegments and SPPSchedulerSegmentsInheritance.
    """

    def __init__(self, build_sets, priority_cmp=prio_low_wins_equal_fifo):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp
        self._build_sets = build_sets

    @staticmethod
    def accept_model(chains, m):
        for c in chains:
            # only the first task may have multiple predecessors
            for t in c.tasks[1:]:
                if isinstance(t, model.Junction):
                    logger.error("Task %s must not have multiple predecessors." % (t))
                    return False

            # there is no task that has a strict predecessor in another chain
            if m.predecessors(c.tasks[0], only_strong=True):
                logger.error("Task %s must not have a strict predecessor that is not in the same chain." % (c.tasks[0]))
                return False

        return True

    def _get_min_chain_prio(self, taskchain):
        """ returns the minimum priority within the given taskchain and the last task with this priority """
        min_prio = taskchain.tasks[0].scheduling_parameter
        min_prio_task = taskchain.tasks[0]
        for t in taskchain.tasks:
            if min_prio == t.scheduling_parameter or self.priority_cmp(min_prio, t.scheduling_parameter):
                min_prio = t.scheduling_parameter
                min_prio_task = t

        return min_prio, min_prio_task

    def _potential_blockers(self, A, B, model):
        """ implements Def. 4.3.41 """

        blockers = set()
        cur_len = -1
        while cur_len < len(blockers):
            cur_len = len(blockers)

            for tj in model.tasks - A:
                for ti in (B | blockers) - model.predecessors(tj, recursive=True, only_strong=True) \
                                           - model.successors(tj, recursive=True, only_strong=True):
                    if ti is not tj and model.allocations[ti].keys() & model.allocations[tj].keys():
                        blockers.add(tj)

        return blockers

    def _prio_sets(self, taskchain, min_prio):
        higher = set()
        for t in taskchain.resource().tasks - set(taskchain.tasks):
            if self.priority_cmp(t.scheduling_parameter, min_prio):
                higher.add(t)

        blockers = self._potential_blockers(higher | set(taskchain.tasks),
                                            higher | set(taskchain.tasks),
                                            taskchain.resource().model)

        medium = set()
        for tj in taskchain.resource().tasks - set(taskchain.tasks):
            for ti in blockers:
                if self.priority_cmp(tj.scheduling_parameter, ti.scheduling_parameter):
                    medium.add(tj)

        lower = taskchain.resource().tasks - medium - blockers - higher

        return higher, medium, blockers, lower

    def _chain_sets(self, chains, model):
        strict_chains = set()
        other_chains  = set()

        for c in chains:
            strict = True
            if len(c.tasks) > 1:
                for src, dst in zip(c.tasks[:-1], c.tasks[1:]):
                    if not model.is_strong_precedence(src, dst):
                        strict = False
                        break
            else:
                strict = False

            if strict:
                strict_chains.add(c)
            else:
                other_chains.add(c)

        return strict_chains, other_chains

    def _last_strict(self, taskchain):
        tS = taskchain.tasks[-1]
        last_strict = {tS}
        for src, dst in zip(reversed(taskchain.tasks[:-1]), reversed(taskchain.tasks[1:])):
            if taskchain.resource().model.is_strong_precedence(src, dst):
                last_strict.add(src)
                tS = src
            else:
                break

        return last_strict, tS

    def _crit_segment(self, segments):
        """ find the critical segment in other segments (Theorem 4.3.31) """
        crit_seg = None
        max_cet = 0
        for c, segs in segments.items():
            for s in segs:
                cet = sum([t.wcet for t in s])
                if cet > max_cet:
                    crit_seg = s
                    max_cet = cet

        return crit_seg

    def _get_segments(self, taskchain, lower):
        # split interference into head and deferred segments

        head_segments = dict()
        deferred_segments = dict()

        for tc in taskchain.resource().chains - {taskchain}:
            head_segments[tc] = set()
            deferred_segments[tc] = list()
            deferred_segments[tc].append(set())
            head = True
            for t in tc.tasks:
                if t in lower:
                    head = False
                    if deferred_segments[tc][-1]:
                        deferred_segments[tc].append(set())
                    continue

                if head:
                    # add task to head segment
                    head_segments[tc].add(t)
                else:
                    # add task to to a deferred segment
                    deferred_segments[tc][-1].add(t)

            if head:
                del deferred_segments[tc][-1]

        return head_segments, deferred_segments

    def _compute_cet(self, taskchain, q):
        """ computes lower bound on b_plus """
        wcet = 0
        for t in taskchain.tasks:
            wcet += t.wcet

        return q * wcet

    def _compute_interference(self, taskset, w):
        """ computes independent-interference part in Def. 4.3.17 """
        s = 0
        for t in taskset:
            # tasks can be in multiple chains but the decomposition enforces that
            #   there is only a single input event model for every task
            #   the unmodified input event models are propagated across the chain (cf. bind_taskchain())
            s += t.wcet * t.in_event_model.eta_plus(w)

        return s

    def _compute_self_interference(self, taskset, q, w):
        """ computes self-interference part in Def. 4.3.17 """
        s = 0
        for t, f in taskset.items():
            s += t.wcet * f(q, t.in_event_model.eta_plus(w))

        return s

    def _compute_deferred_interference(self, taskset):
        """ computes deferred-interference part in Def. 4.3.17 """
        s = 0
        for t, n in taskset.items():
            s += t.wcet * n

        return s

    def b_min(self, task, q):
        bcet = 0
        for t in task.chain.tasks:
            bcet += t.bcet

        return q * bcet

    def stopping_condition(self, task, q, w):
        """ uses scheduling horizon to decide on stopping condition """

        # if there are no new activations when the current scheduling horizon has been completed, we terminate
        if task.in_event_model.delta_min(q + 1) >= self.scheduling_horizon(task, q, w):
            return True
        return False

    def scheduling_horizon(self, task, q, w, details=None, compute_b_plus=False):
        """ calculates scheduling horizon to implement the stopping condition, or b_plus if compute_b_plus=True """
        assert hasattr(task, 'chain'), "scheduling_horizon called on the wrong task"

        taskchain = task.chain

        while True:
            w_new = self._compute_self_interference(taskchain._T, q, w) + \
                    self._compute_deferred_interference(taskchain._D)

            tail_wcet = 0
            if compute_b_plus and hasattr(taskchain, '_B'):
                # omit non-preemptible tails
                w_new += self._compute_interference(taskchain._I-taskchain._B, w)

                last_strict, tmp = self._last_strict(taskchain)
                tail_wcet = sum([t.wcet for t in last_strict])
                w_new += self._compute_interference(taskchain._B, w-tail_wcet)
            else:
                w_new += self._compute_interference(taskchain._I, w)

            if w == w_new:
                if details is not None:
                    for t, f in taskchain._T.items():
                        arg = t.in_event_model.eta_plus(w)
                        details[str(t)+':f(q)*WCET'] = str(f(q,arg)) + '*' + str(t.wcet) + '=' + str(f(q,arg) * t.wcet)

                    for t in taskchain._I:
                        assert(t.in_event_model.eta_plus(w) > 0)
                        details[str(t)+":eta(w)*WCET"]  = str(t.in_event_model.eta_plus(w)) \
                                                        + "*" + str(t.wcet) + "=" \
                                                        + str(t.in_event_model.eta_plus(w) * t.wcet)

                    for t, n in taskchain._D.items():
                        if n > 0:
                            details[str(t)+":n*WCET"]       = str(n) + "*" + str(t.wcet) + "=" + str(n * t.wcet)

                    # details argument is only provided when called with compute_b_plus=True
                    if hasattr(taskchain, '_B'):
                        for t in taskchain._B:
                            assert t not in taskchain._T
                            details[str(t)+":eta(w)*WCET"]  = str(t.in_event_model.eta_plus(w-tail_wcet)) \
                                                            + "*" + str(t.wcet) + "=" \
                                                            + str(t.in_event_model.eta_plus(w-tail_wcet) * t.wcet)

                return w

            w = w_new

    def b_plus(self, task, q, details=None, **kwargs):
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)
        assert hasattr(task, 'chain'), "b_plus called on the wrong task"

        taskchain = task.chain

        w = self._compute_cet(taskchain, q)

        # only build the sets once, assuming that the resource's task set never changes
        #    FIXME if the analysis should ever be re-started after changing the task set,
        #          the sets must be recomputed
        if not hasattr(taskchain, '_D'):
            self._build_sets(taskchain)

        w = self.scheduling_horizon(task, q, w=w, details=details, compute_b_plus=True)

        return w

class SPPSchedulerSegmentsUniform(SPPSchedulerSegmentsBase):
    """ Implements Theorem 4.3.37 from TODO """

    def __init__(self):
        SPPSchedulerSegmentsBase.__init__(self, build_sets=self._build_sets)

    def accept_model(self, chains, model):
        if not SPPSchedulerSegmentsBase.accept_model(chains, model):
            return False

        used_execs = set()
        tasks = set()
        for c in chains:
            # check precedence relations
            if len(c.tasks) > 2:
                ptype = model.is_strong_precedence(c.tasks[0], c.tasks[1])
                for src, dst in zip(c.tasks[1:-1], c.tasks[2:]):
                    if model.is_strong_precedence(src,dst) != ptype:
                        logger.error("Chain %s switches precedence type between task %s and %s." % (c, src, dst))
                        return False

            # there are no strict precedence relations between different chains
            for t in c.tasks:
                for d in t.next_tasks - set(c.tasks):
                    if model.is_strong_precedence(t, d):
                        logger.error("Strict precedence relation between tasks of different chains(%s and %s)." % (t, d))
                        return False


            # only the last task may have multiple successors
            for t in c.tasks[:-1]:
                if len(t.next_tasks) > 1:
                    logger.error("Task %s must not have multiple successors." % (t))
                    return False

            # execution contexts must not be used by tasks of different chains
            my_execs = set()
            for t in c.tasks:
                my_execs.update(model.allocations[t].keys())
            for e in my_execs:
                if e in used_execs:
                    logger.error("Execution context %s is used by multiple chains." % e)
                    return False
            used_execs.update(my_execs)

            # tasks must be present in exactly one task chain
            for t in c.tasks:
                if t in tasks:
                    logger.error("Task %s is in multiple chains." % t)
                    return False
                tasks.add(t)

        return True

    def _build_sets(self, taskchain):
        taskchain._I = set()
        taskchain._D = dict()
        taskchain._T = dict()

        model = taskchain.resource().model

        # compute minimum priority of the chain
        min_prio, min_prio_task = self._get_min_chain_prio(taskchain)

        ####################
        # self-interference
        if len(taskchain.tasks) == 1:
            # take a shortcut for single-task chains
            for t in taskchain.tasks:
                taskchain._T[t] = lambda q, eta: q
        elif model.is_strong_precedence(taskchain.tasks[0], taskchain.tasks[1]):
            # set self-interference according to Theorem 4.3.23
            for t in taskchain.tasks:
                taskchain._T[t] = lambda q, x: q
        else:
            head = set()
            tail = set()
            # split chain into head and tail according to Def. 4.3.20
            for t in taskchain.tasks:
                if len(tail) == 0:
                    if t is not min_prio_task:
                        head.add(t)
                    else:
                        tail.add(t)
                else:
                    tail.add(t)

            # set self-interference according to Theorem 4.3.23
            for t in head:
                taskchain._T[t] = lambda q,eta: max(eta, q)
            for t in tail:
                taskchain._T[t] = lambda q,eta: q

        ########################
        # deferred interference
        lower = set()
        for t in taskchain.resource().tasks:
            if not self.priority_cmp(t.scheduling_parameter, min_prio):
                lower.add(t)
        head_segs, other_segs = self._get_segments(taskchain, lower)

        # process head segments
        for c, head in head_segs.items():
            if len(c.tasks) > 1 and other_segs[c] and model.is_strong_precedence(c.tasks[0], c.tasks[1]):
                # Corollary 4.3.36
                for t in head:
                    taskchain._D[t] = 1
            else:
                # head segments of weak precedence chains and high-priority chains are normal interferers
                for t in head:
                    taskchain._I.add(t)

        crit_seg = self._crit_segment(other_segs)

        # Corollary 4.3.33
        for c, segs in other_segs.items():
            for s in segs:
                if s is crit_seg:
                    for t in s:
                        taskchain._D[t] = 1
                else:
                    for t in s:
                        taskchain._D[t] = 0

        # chain tasks do not occur in _I or _D
        for t in set(taskchain.tasks):
                assert t not in taskchain._I and t not in taskchain._D, "Taskchain task %s in D or I." % t

        # sanity check (all high priority tasks occur in _I or _D
        for t in taskchain.resource().tasks - set(taskchain.tasks) - lower:
            if self.priority_cmp(t.scheduling_parameter, min_prio):
                assert t in taskchain._I or t in taskchain._D, "Task %s not in D or I." % t

class SPPSchedulerSegments(SPPSchedulerSegmentsBase):
    """ Implements Corollary 4.3.58 for priority-inversion case. """

    def __init__(self):
        SPPSchedulerSegmentsBase.__init__(self, build_sets=self._build_sets)

    def accept_model(self, chains, model):
        return SPPSchedulerSegmentsBase.accept_model(chains, model)

    def _build_sets(self, taskchain):
        taskchain._I = set()
        taskchain._B = set()
        taskchain._D = dict()
        taskchain._T = dict()

        model = taskchain.resource().model

        # compute minimum priority of the chain
        min_prio, min_prio_task = self._get_min_chain_prio(taskchain)

        # build priority sets
        higher, medium, blocker, lower = self._prio_sets(taskchain, min_prio)

        # separate purely strict from other chains
        strict_chains, other_chains = self._chain_sets(taskchain.resource().chains, model)

        ####################
        # self-interference
        if len(taskchain.tasks) == 1:
            # shortcut for single-task chains
            taskchain._T[t] = lambda q, eta: q
        elif taskchain in strict_chains:
            # shortcut for purely strict chains
            for t in taskchain.tasks:
                taskchain._T[t] = lambda q, x: q
        else:
            # first, determine whether a t_L exists according to Lemma 4.3.36
            tL = None
            non_strict_succ = (model.successors(min_prio_task, recursive=True)
                             - model.successors(min_prio_task, only_strong=True, recursive=True)) & set(taskchain.tasks)
            if not (self._potential_blockers(non_strict_succ, non_strict_succ, model) & \
                    model.predecessors(min_prio_task, only_strong=True, recursive=True)):
                tL = min_prio_task

            # second, determine whether the chain ends with a strict precedence segment
            last_strict, tS = self._last_strict(taskchain)

            # Def. 4.3.48
            head = set()
            tail = set()
            if last_strict and tL not in last_strict:
                head = model.predecessors(tS, recursive=True) & set(taskchain.tasks)
            elif tL:
                head = model.predecessors(tL, recursive=True) & set(taskchain.tasks)
            else:
                head = set(taskchain.tasks)

            tail = set(taskchain.tasks) - head

            # set self-interference
            for t in head:
                taskchain._T[t] = lambda q,eta: max(eta, q)
            for t in tail:
                taskchain._T[t] = lambda q,eta: q

        ########################
        # deferred interference
        head_segs, other_segs = self._get_segments(taskchain, lower)
        crit_seg = self._crit_segment(other_segs)

        # Corollary 4.3.33
        for c, segs in other_segs.items():
            for s in segs:
                if s is crit_seg:
                    for t in s - set(taskchain.tasks):
                        taskchain._D[t] = 1
                else:
                    for t in s - set(taskchain.tasks):
                        taskchain._D[t] = 0

        # process head segments of purely strict chains
        for c, head in head_segs.items():
            if other_segs[c] and c in strict_chains:
                # Corollary 4.3.36
                for t in head - set(taskchain.tasks):
                    taskchain._D[t] = 1

        # process tasks in head segments that are not already in _D
        for c, head in head_segs.items():
            for t in head - set(taskchain.tasks):
                if t not in taskchain._D:
                    taskchain._I.add(t)

        # sanity check: _I and _D are disjoint
        assert not (taskchain._I & taskchain._D.keys()), \
                   "D and I are not disjoint: %s" % taskchain._I&taskchain._D.keys()

        # sanity check: _T and _I |_D are disjoint
        assert not (taskchain._T.keys() & (taskchain._I | taskchain._D.keys())), \
                   "T and D&I are not disjoint: %s" % (taskchain._T.keys()&(taskchain._I|taskchain._D.keys()))

        # sanity check (all high priority tasks occur in _I or _D
        for t in taskchain.resource().tasks - set(taskchain.tasks) - lower:
            if self.priority_cmp(t.scheduling_parameter, min_prio):
                assert t in taskchain._I or t in taskchain._D, "Task %s not in D or I." % t

        # determine tasks that cannot preempt the last strict segment
        last_strict, first = self._last_strict(taskchain)
        assert len(model.allocations[first].keys()) == 1
        last_ectx = list(model.allocations[first].keys())[0]
        affected = set()
        for t in taskchain._I:
            if last_ectx in model.allocations[t]:
                affected.add(t)
                affected.update(model.successors(t, recursive=True))

        for t in taskchain._I & affected:
            taskchain._B.add(t)


class SPPSchedulerSegmentsInheritance(SPPSchedulerSegmentsBase):
    """ Implements Corollary 4.3.58 for perfect priority inheritance """

    def __init__(self):
        SPPSchedulerSegmentsBase.__init__(self, build_sets=self._build_sets)

    def accept_model(self, chains, model):
        if not SPPSchedulerSegmentsBase.accept_model(chains, model):
            return False

        # check that strict predecessors are mapped to the same scheduling context
        for c in chains:
            if len(c.tasks) > 1:
                for src, dst in zip(c.tasks[:-1], c.tasks[1:]):
                    if model.is_strong_precedence(src, dst):
                        if model.mappings[src] != model.mappings[dst]:
                            logger.error("Strict predecessors %s and %s have different scheduling contexts and thus" \
                                          " violate priority inheritance." % (src, dst))
                            return False

        return True

    def _build_sets(self, taskchain):
        taskchain._I = set()
        taskchain._D = dict()
        taskchain._T = dict()
        taskchain._B = set()

        model = taskchain.resource().model

        # compute minimum priority of the chain
        min_prio, min_prio_task = self._get_min_chain_prio(taskchain)

        # build priority sets
        higher, medium, blocker, lower = self._prio_sets(taskchain, min_prio)
        # due to helping, there are no medium priority tasks
        lower.update(medium-blocker)

        # separate purely strict from other chains
        strict_chains, other_chains = self._chain_sets(taskchain.resource().chains, model)

        ####################
        # self-interference
        if len(taskchain.tasks) == 1:
            # shortcut for single-task chains
            for t in taskchain.tasks:
                taskchain._T[t] = lambda q, eta: q
        elif taskchain in strict_chains:
            # shortcut for purely strict chains
            for t in taskchain.tasks:
                taskchain._T[t] = lambda q, x: q
        else:
            # first, determine t_L according to Lemma 4.3.55
            tL = None
            spreds = model.predecessors(min_prio_task, only_strong=True, recursive=True) & set(taskchain.tasks)
            if not spreds:
                tL = min_prio_task
            elif len(spreds) == 1:
                tL = list(spreds)[0]
            else:
                for t in taskchain.tasks:
                    if t in spreds:
                        tL = t
                        break

            # Def. 4.3.57
            head = model.predecessors(tL, recursive=True) & set(taskchain.tasks)
            tail = set(taskchain.tasks) - head

            # set self-interference
            for t in head:
                taskchain._T[t] = lambda q,eta: max(eta, q)
            for t in tail:
                taskchain._T[t] = lambda q,eta: q

        ########################
        # deferred interference
        head_segs, other_segs = self._get_segments(taskchain, lower)
        crit_seg = self._crit_segment(other_segs)

        # Corollary 4.3.33
        for c, segs in other_segs.items():
            for s in segs:
                if s is crit_seg:
                    for t in s - set(taskchain.tasks):
                        taskchain._D[t] = 1
                else:
                    for t in s - set(taskchain.tasks):
                        taskchain._D[t] = 0

        # process head segments of purely strict chains and tasks after the first B segment
        for c, head in head_segs.items():
            if other_segs[c] and c in strict_chains:
                # Corollary 4.3.36
                for t in head - set(taskchain.tasks):
                    taskchain._D[t] = 1
            else:
                after_B = False
                for t in head - set(taskchain.tasks):
                    if after_B or t in blocker:
                        after_B = True
                        taskchain._D[t] = 1

        # process tasks in head segments that are not already in _D
        for c, head in head_segs.items():
            for t in head - set(taskchain.tasks):
                if t not in taskchain._D:
                    taskchain._I.add(t)

        # sanity check: _I and _D are disjoint
        assert not (taskchain._I & taskchain._D.keys()), \
                   "D and I are not disjoint: %s" % taskchain._I&taskchain._D.keys()

        # sanity check: _T and _I |_D are disjoint
        assert not (taskchain._T.keys() & (taskchain._I | taskchain._D.keys())), \
                   "T and D&I are not disjoint: %s" % (taskchain._T.keys()&(taskchain._I|taskchain._D.keys()))

        # sanity check (all high priority tasks occur in _I or _D
        for t in taskchain.resource().tasks - set(taskchain.tasks) - lower:
            if self.priority_cmp(t.scheduling_parameter, min_prio):
                assert t in taskchain._I or t in taskchain._D, "Task %s not in D or I." % t

        # determine tasks that cannot preempt the last strict segment
        last_strict, first = self._last_strict(taskchain)
        assert len(model.allocations[first].keys()) == 1
        last_ectx = list(model.allocations[first].keys())[0]
        affected = set()
        for t in taskchain._I:
            if last_ectx in model.allocations[t]:
                affected.add(t)
                affected.update(model.successors(t, recursive=True))

        for t in taskchain._I & affected:
            taskchain._B.add(t)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
