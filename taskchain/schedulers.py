"""
| Copyright (C) 2015 Johannes Schlatow
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


    def b_plus(self, task, q, details=None):
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


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
