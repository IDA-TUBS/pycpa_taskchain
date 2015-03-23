""" 
| Copyright (C) 2015 Johannes Schlatow
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Johannes Schlatow

Description
-----------
TODO
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals
from __future__ import division

from pycpa import options
from pycpa import model
from pycpa import path_analysis


def end_to_end_latency(path, task_results, n=1 , task_overhead=0,
                       path_overhead=0, **kwargs):
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

    newpath = model.Path(path.name, [path.tasks[0]])
    return path_analysis.end_to_end_latency(newpath, task_results, n, task_overhead, path_overhead)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
