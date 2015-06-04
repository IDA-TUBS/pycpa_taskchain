""" 
| Copyright (C) 2015 Johannes Schlatow
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Johannes Schlatow

Description
-----------
Improved worst-case end-to-end latency analysis for task chains
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

from pycpa import options
from pycpa import model
from pycpa import path_analysis
from . import schedulers


def end_to_end_latency(path, task_results, n=1 , task_overhead=0,
                       path_overhead=0, injection_rate='max', **kwargs):
    """ Computes the worst-/best-case e2e latency for n tokens to pass the path.
    The constant path.overhead is added to the best- and worst-case latencies.

    :param path: the path
    :type path: model.Path
    :param n:  amount of events
    :type n: integer
    :param task_overhead: A constant task_overhead is added once per task to both min and max latency
    :type task_overhead: integer
    :param path_overhead:  A constant path_overhead is added once per path to both min and max latency
    :type path_overhead: integer
    :rtype: tuple (best-case latency, worst-case latency)
    """

    # busy-window-based e2e analysis of a task chain
    #  4. what about task_overhead and path_overhead?

    scheduler = schedulers.SimpleChainScheduler()
    lmax = scheduler.compute_wcrt(path.tasks[0])
    lmin = scheduler.compute_bcrt(path.tasks[0])

    if injection_rate == 'max':
        # add the eastliest possible release of event n
        lmax += path.tasks[0].in_event_model.delta_min(n)

    elif injection_rate == 'min':
        # add the latest possible release of event n
        lmax += path.tasks[0].in_event_model.delta_plus(n)

    # add the earliest possible release of event n
    lmin += path.tasks[0].in_event_model.delta_min(n)

    # FIXME: include path and task overhead
    assert(path_overhead == 0)
    assert(task_overhead == 0)

    return lmin, lmax

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
