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

class SPPScheduler(analysis.Scheduler):
    """ Improved Static-Priority-Preemptive Scheduler

    Priority is stored in task.scheduling_parameter,
    by default numerically lower numbers have a higher priority

    Policy for equal priority is FCFS (i.e. max. interference).
    """


    def __init__(self, priority_cmp=prio_low_wins_equal_fifo):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp

    def _get_min_prio_tail(self, task):
        assert(task.scheduling_parameter != None)

        min_prio = task.scheduling_parameter
        tail = set([task])
        for ti in task.next_tasks:
            if ti.resource != task.resource:
                # skip tasks on other resources
                continue
            [subtree_min_prio, subtail] = self._get_min_prio_tail(ti)
            if self.priority_cmp(min_prio, subtree_min_prio):
                min_prio = subtree_min_prio

            tail.update(subtail)

        return [min_prio, tail]

    def _build_sets(self, task):

        # compute minimum priority of the chain
        [min_prio, tail] = self._get_min_prio_tail(task)

        S = set()
        I = set()
        for ti in task.get_resource_interferers():
            assert(ti.scheduling_parameter != None)
            assert(ti.resource == task.resource)
            if self.priority_cmp(ti.scheduling_parameter, task.scheduling_parameter):
                # iterate head set (on same resource)
                tj = ti
                while tj.prev_task != None and tj.prev_task.resource == ti.resource:
                    tj = tj.prev_task
                    if not self.priority_cmp(tj.scheduling_parameter, min_prio):
                        # task is stalled
                        S.add(ti)
                        tj = None
                        break

                if tj != None:
                    # task is not stalled
                    I.add(ti)

        return [S,I,tail,min_prio]

    def head(self, task, min_prio):
        assert(task is not None)
        if task.prev_task is None:
            return set([task])
        
        # predecessor must be on the same resource
        if task.prev_task.resource != task.resource:
            return set([task])

        # predecessor can not be scheduled
        if not self.priority_cmp(task.prev_task.scheduling_parameter, min_prio):
            return set([task])
        
        # else:
        res = self.head(task.prev_task, min_prio)
        res.add(task)
        return res

    def compute_cet(self, task, q):
        # logging.debug("e: %d", q * task.wcet)
        return q * task.wcet

    def compute_blocking(self, S, q, tail, min_prio):
        s = 0
        for ti in S:
            if ti in tail:
                n = min(q,ti.in_event_model.eta_plus_closed(0))
            else:
                # task is either activated by buffered events at 0 or by its predecessor
                n = max([tj.in_event_model.eta_plus_closed(0) for tj in self.head(ti, min_prio)])

            assert(n > 0)
            s += ti.wcet * n
            
#        logging.debug("S: %d", s)
        return s

    def compute_interference(self, I, w, q, tail):
        s = 0
        for ti in I:
            n = ti.in_event_model.eta_plus(w)
            if ti in tail:
                n = min(q,n)
            s += ti.wcet * n

#        logging.debug("I: %d", s)
        return s

    def b_plus(self, task, q, details=None):
        """ This corresponds to Equation ... TODO """
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        w = q * task.wcet

        while True:
#            logging.debug("w: %d", w)
            s = 0

            [S,I,tail,min_prio] = self._build_sets(task)
            w_new = self.compute_cet(task, q) + self.compute_blocking(S, q, tail, min_prio) + self.compute_interference(I, w, q, tail)

#             print ("w_new: ", w_new)
            if w == w_new:
                assert(w >= q * task.wcet)
                if details is not None:
                    details['q*WCET'] = str(q) + '*' + str(task.wcet) + '=' + str(q * task.wcet)
                    for ti in S:
                        if ti in tail and q < ti.in_event_model.eta_plus_closed(0):
                            details[str(ti)+":q*WCET"]      = str(q) \
                                                              + "*" + str(ti.wcet) + "=" \
                                                              + str(q * ti.wcet)
                        else:
                            details[str(ti)+":eta(0)*WCET"] = str(ti.in_event_model.eta_plus_closed(0)) \
                                                              + "*" + str(ti.wcet) + "=" \
                                                              + str(ti.in_event_model.eta_plus_closed(0) * ti.wcet)
                    for ti in I:
                        if ti in tail and q < ti.in_event_model.eta_plus(w):
                            details[str(ti)+":q*WCET"]      = str(q) \
                                                              + "*" + str(ti.wcet) + "=" \
                                                              + str(q * ti.wcet)
                        else:
                            details[str(ti)+":eta*WCET"]    = str(ti.in_event_model.eta_plus(w)) \
                                                              + "*" + str(ti.wcet) + "=" \
                                                              + str(ti.in_event_model.eta_plus(w) * ti.wcet)

                return w

            w = w_new

class ChainScheduler(SPPScheduler):
    """ Static-Priority-Preemptive Scheduler for task chains

    Priority is stored in task.scheduling_parameter,
    by default numerically lower numbers have a higher priority

    Policy for equal priority is FCFS (i.e. max. interference).

    Computes busy window for the whole task chain.
    """


    def __init__(self, priority_cmp=prio_low_wins_equal_fifo):
        analysis.Scheduler.__init__(self)

        # # priority ordering
        self.priority_cmp = priority_cmp

    def _build_sets(self, task):
        # compute minimum priority of the chain and tail
        [min_prio, tail] = self._get_min_prio_tail(task)

        S = set()
        I = set()
        interferers = set()
        for ti in tail:
            interferers.update(ti.get_resource_interferers())

        for ti in interferers:
            # skip tail
            if ti in tail:
                continue

            assert(ti.scheduling_parameter != None)
            assert(ti.resource == task.resource)

            if self.priority_cmp(ti.scheduling_parameter, task.scheduling_parameter):
                # iterate head set (on same resource)
                tj = ti
                while tj.prev_task != None and tj.prev_task.resource == ti.resource:
                    tj = tj.prev_task
                    if not self.priority_cmp(tj.scheduling_parameter, min_prio):
                        # task is stalled
                        S.add(ti)
                        tj = None
                        break

                if tj != None:
                    # task is not stalled
                    I.add(ti)

        return [S,I,tail,min_prio]

    def compute_cet(self, tail, q):
        # logging.debug("e: %d", q * task.wcet)
        s = 0
        for ti in tail:
            s += q * ti.wcet

        return s

    def compute_blocking(self, S, min_prio):
        s = 0
        for ti in S:
            n = 0
            for tj in self.head(ti, min_prio):
                assert(tj.in_event_model.eta_plus_closed(0) > 0)
                n = max(n, tj.in_event_model.eta_plus_closed(0))

            s += ti.wcet * n
            
#        logging.debug("S: %d", s)
        return s

    def compute_interference(self, I, w):
        s = 0
        for ti in I:
            s += ti.wcet * ti.in_event_model.eta_plus(w)

#        logging.debug("I: %d", s)
        return s

    def b_plus(self, task, q, details=None):
        """ This corresponds to Equation ... TODO """
        assert(task.scheduling_parameter != None)
        assert(task.wcet >= 0)

        w = q * task.wcet

        while True:
#            logging.debug("w: %d", w)
            s = 0

            [S,I,tail,min_prio] = self._build_sets(task)
            w_new = self.compute_cet(tail, q) + self.compute_blocking(S,min_prio) + self.compute_interference(I, w)

#             print ("w_new: ", w_new)
            if w == w_new:
                assert(w >= q * task.wcet)
                if details is not None:
                    for ti in tail:
                        details[str(ti)+":q*WCET"]      = str(q) \
                                                          + "*" + str(ti.wcet) + "=" \
                                                          + str(q * ti.wcet)
                    for ti in S:
                        details[str(ti)+":eta(0)*WCET"] = str(ti.in_event_model.eta_plus_closed(0)) \
                                                          + "*" + str(ti.wcet) + "=" \
                                                          + str(ti.in_event_model.eta_plus_closed(0) * ti.wcet)
                    for ti in I:
                        details[str(ti)+":eta*WCET"]    = str(ti.in_event_model.eta_plus(w)) \
                                                          + "*" + str(ti.wcet) + "=" \
                                                          + str(ti.in_event_model.eta_plus(w) * ti.wcet)

                return w

            w = w_new

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
