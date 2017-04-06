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
        """ This corresponds to Equation ... TODO """
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        assert hasattr(task, 'chain'), "b_plus called on the wrong task"

        taskchain = task.chain

        w = self._compute_cet(taskchain, q)

        while True:
            s = 0

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
                                                          + str(t.in_event_model.eta_plus(w) * t.wcet)
                    for t in H:
                        details[str(t)+":eta*WCET"]    = str(max(taskchain.tasks[0].in_event_model.eta_plus(w)-q,0)) \
                                                          + "*" + str(t.wcet) + "=" \
                                                          + str(t.in_event_model.eta_plus(w) * t.wcet)

                    for t in D:
                        details[str(t)+":WCET"]        = str(t.wcet)

                return w

            w = w_new

class SPPSchedulerSync(SPPSchedulerSimple):

    def __init__(self):
        SPPSchedulerSimple.__init__(self, build_sets=self._build_sets)

    def _build_sets(self, taskchain):

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
    """ Computes a task chain busy window computation (scheduler-independent).
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

    Computes busy window of an entire task chain.
    """

    def __init__(self, priority_cmp=prio_low_wins_equal_fifo, candidate_search=False):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp

        self.perform_candidate_search = candidate_search
        self.candidates = None

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
            task_ec_bounds[t] = TaskChainBusyWindow.MinMaxEventCountBound(upper_bounds=set([inf]))
            if t in bw.lower_ec_bounds:
                # if there is a lower bound (i.e. q-events for the chain's tasks), add min/max bound
                task_ec_bounds[t].add_lower_bound(bw.lower_ec_bounds[t])

        # add event count bounds based on input event models of chains
        for c in resource.chains:
            for t in c.tasks:
                task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.ArrivalEventCountBound(c.tasks[0].in_event_model))

        # a task can only interfere as once if there is a lower-priority or strong predecessor that cannot execute at all
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
        last_chain_task = bw.taskchain.tasks[-1]
        task_ec_bounds[last_chain_task].add_upper_bound(TaskChainBusyWindow.StaticEventCountBound(q))

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
                    if len(lp_bounds) == 0:
                        task_ec_bounds[t].add_upper_bound(TaskChainBusyWindow.StaticEventCountBound(0))
                    else:
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
        """ This corresponds to Equation ... TODO """
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

        return w


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
