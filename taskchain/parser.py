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
from __future__ import unicode_literals
from __future__ import division

import math
import logging
import copy
import warnings

from pycpa import model as pycpa_model
from . import model

from pygraphml import Graph
from pygraphml import GraphMLParser

logger = logging.getLogger(__name__)

class Graphml(GraphMLParser):

    def model_from_file(self, filename):
        g = self.parse(filename)

        m = model.ResourceModel(g.name)

        # store added objects by their corresponding task nodes
        objects = dict()

        # iterate nodes
        for n in g.nodes():
            if n['type'] == 'task':
                objects[n] = m.add_task(pycpa_model.Task(n['id']))
                if n['period'] != 0:
                    objects[n].in_event_model = pycpa_model.PJdEventModel(P=n['period'], J=n['jitter'])

                if n['wcet'] != 0:
                    objects[n].wcet = n['wcet']

                if n['bcet'] != 0:
                    objects[n].bcet = n['bcet']

                if 'scheduling_parameter' in n.attributes():
                    objects[n].scheduling_parameter = n['scheduling_parameter']

            elif n['type'] == 'sched':
                objects[n] = m.add_scheduling_context(model.SchedulingContext(n['id']))
            elif n['type'] == 'exec':
                objects[n] = m.add_execution_context(model.ExecutionContext(n['id']))
            
        # iterate edges
        for e in g.edges():
            if e.target()['type'] == "task":
                edgetype = e.source()['type']
            else:
                edgetype = e.target()['type']

            if edgetype == "task":
                m.link_tasks(objects[e.source()], objects[e.target()])
            elif edgetype == "sched":
                m.assign_scheduling_context(objects[e.source()], objects[e.target()])
            elif edgetype == "exec":
                if e.source()['type'] == 'task':
                    task = objects[e.source()]
                    ctx = objects[e.target()]
                    blocking = True
                else:
                    task = objects[e.target()]
                    ctx = objects[e.source()]
                    blocking = False

                m.assign_execution_context(task, ctx, blocking=blocking)

        return m

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
