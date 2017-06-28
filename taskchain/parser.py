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
from pycpa import util
from . import model

from pygraphml import Graph
from pygraphml import GraphMLParser

logger = logging.getLogger(__name__)

class Graphml(GraphMLParser):

    def model_from_file(self, filename, resname=None, from_time_base=util.us, to_time_base=util.us):
        models = self.models_from_file(filename, from_time_base, to_time_base)

        if resname is not None:
            return models[resname]
        elif len(models) == 1:
            return list(models.values())[0]
        else:
            raise Exception("error")

    def models_from_file(self, filename, from_time_base=util.us, to_time_base=util.us):
        g = self.parse(filename)

        models = dict()

        # store added objects by their corresponding task nodes
        objects = dict()

        # iterate nodes
        for n in g.nodes():
            if 'resource' in n.attributes():
                res = n['resource']
            else:
                res = 'unknown'

            if res not in models:
                models[res] = model.ResourceModel(res)

            if n['type'] == 'task':

                objects[n] = models[res].add_task(pycpa_model.Task(n['id']))
                if n['period'] != 0:
                    objects[n].in_event_model = pycpa_model.PJdEventModel(
                            P=util.time_to_time(n['period'], from_time_base, to_time_base),
                            J=util.time_to_time(n['jitter'], from_time_base, to_time_base))

                if n['wcet'] != 0:
                    objects[n].wcet = util.time_to_time(n['wcet'], from_time_base, to_time_base)

                if n['bcet'] != 0:
                    objects[n].bcet = util.time_to_time(n['bcet'], from_time_base, to_time_base)

                if 'scheduling_parameter' in n.attributes():
                    objects[n].scheduling_parameter = n['scheduling_parameter']

                objects[n].resname = res

            elif n['type'] == 'sched':
                objects[n] = models[res].add_scheduling_context(model.SchedulingContext(n['id']))

                if 'scheduling_parameter' in n.attributes():
                    objects[n].priority = n['scheduling_parameter']

            elif n['type'] == 'exec':
                objects[n] = models[res].add_execution_context(model.ExecutionContext(n['id']))
            
        # iterate edges
        for e in g.edges():
            if e.target()['type'] == "task":
                res = objects[e.target()].resname
                edgetype = e.source()['type']
            else:
                res = objects[e.source()].resname
                edgetype = e.target()['type']

            if edgetype == "task":
                if objects[e.source()].resname == objects[e.target()].resname:
                    models[res].link_tasks(objects[e.source()], objects[e.target()])
                else:
                    objects[e.source()].link_dependent_task(objects[e.target()])

            elif edgetype == "sched":
                models[res].assign_scheduling_context(objects[e.source()], objects[e.target()])
            elif edgetype == "exec":
                if e.source()['type'] == 'task':
                    task = objects[e.source()]
                    ctx = objects[e.target()]
                    blocking = True
                else:
                    task = objects[e.target()]
                    ctx = objects[e.source()]
                    blocking = False

                models[res].assign_execution_context(task, ctx, blocking=blocking)

        return models

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
