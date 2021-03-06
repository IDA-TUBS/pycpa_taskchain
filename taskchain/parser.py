"""
| Copyright (C) 2020 Johannes Schlatow
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

from networkx.readwrite import graphml
import networkx as nx

import typing

logger = logging.getLogger(__name__)

class Graphml:

    @staticmethod
    def model_to_file(m: model.ResourceModel, filename, from_time_base=util.us, to_time_base=util.us):
        # first, put model into a networkx graph
        g = nx.DiGraph(name=m.name)

        for t in m.tasks:
            g.add_node(t.name, type='task',
                               wcet=util.time_to_time(t.wcet, from_time_base, to_time_base),
                               bcet=util.time_to_time(t.bcet, from_time_base, to_time_base))

            if isinstance(t.in_event_model, pycpa_model.PJdEventModel):
                g.nodes[t.name]['period'] = util.time_to_time(t.in_event_model.P, from_time_base, to_time_base)
                g.nodes[t.name]['jitter'] = util.time_to_time(t.in_event_model.J, from_time_base, to_time_base)

        for e in [e.name for e in m.exec_ctxs]:
            g.add_node(e, type='exec')

        for s in m.sched_ctxs:
            g.add_node(s.name, type='sched',
                               scheduling_parameter=s.priority)

        for src, dsts in m.tasklinks.items():
            for dst in dsts:
                g.add_edge(src.name, dst.name)

        for t, data in m.allocations.items():
            for e, blocking in data.items():
                if blocking:
                    g.add_edge(t.name, e.name)
                else:
                    g.add_edge(e.name, t.name)

        for t, s in m.mappings.items():
            g.add_edge(t.name, s.name)

        # second, write GraphML
        nx.write_graphml(g, filename, prettyprint=True)

    def model_from_file(self, filename, resname=None, from_time_base=util.us, to_time_base=util.us):
        models = self.models_from_file(filename, from_time_base, to_time_base)

        if resname is not None:
            return models[resname]
        elif len(models) == 1:
            return list(models.values())[0]
        else:
            raise Exception("error")

    def apply_defaults(self, g):
        for attr, default in g.graph['node_default'].items():
            for node, data in g.nodes(data=True):
                if attr not in data:
                    data[attr] = default

        for attr, default in g.graph['edge_default'].items():
            for u, v, data in g.edges(data=True):
                if attr not in data:
                    data[attr] = default

    def models_from_file(self, filename, from_time_base=util.us, to_time_base=util.us):
        g = graphml.read_graphml(filename, node_type=str, edge_key_type=str)
        self.apply_defaults(g)

        models = dict()

        # store added objects by their corresponding task nodes
        objects = dict()

        # iterate nodes
        for n, data in g.nodes(data=True):
            if 'resource' in data:
                res = data['resource']
            elif 'name' in g.graph:
                res = g.graph['name']
            else:
                res = 'unknown'

            if res not in models:
                models[res] = model.ResourceModel(res)

            if data['type'] == 'task':

                objects[n] = models[res].add_task(pycpa_model.Task(n))
                if 'period' in data and data['period'] != 0:
                    objects[n].in_event_model = pycpa_model.PJdEventModel(
                            P=util.time_to_time(data['period'], from_time_base, to_time_base),
                            J=util.time_to_time(data['jitter'], from_time_base, to_time_base))

                if data['wcet'] != 0:
                    objects[n].wcet = util.time_to_time(data['wcet'], from_time_base, to_time_base)

                if data['bcet'] != 0:
                    objects[n].bcet = util.time_to_time(data['bcet'], from_time_base, to_time_base)

                if 'scheduling_parameter' in data:
                    objects[n].scheduling_parameter = data['scheduling_parameter']

                objects[n].resname = res

            elif data['type'] == 'sched':
                objects[n] = models[res].add_scheduling_context(model.SchedulingContext(n))

                if 'scheduling_parameter' in data:
                    objects[n].priority = data['scheduling_parameter']

            elif data['type'] == 'exec':
                objects[n] = models[res].add_execution_context(model.ExecutionContext(n))

        # iterate edges
        for source, target, data in g.edges(data=True):
            if g.nodes[target]['type'] == "task":
                res = objects[target].resname
                edgetype = g.nodes[source]['type']
            else:
                res = objects[source].resname
                edgetype = g.nodes[target]['type']

            if edgetype == "task":
                if objects[source].resname == objects[target].resname:
                    models[res].link_tasks(objects[source], objects[target])
                else:
                    objects[source].link_dependent_task(objects[target])

            elif edgetype == "sched":
                models[res].assign_scheduling_context(objects[source], objects[target])
            elif edgetype == "exec":
                if g.nodes[source]['type'] == 'task':
                    task = objects[source]
                    ctx = objects[target]
                    blocking = True
                else:
                    task = objects[target]
                    ctx = objects[source]
                    blocking = False

                models[res].assign_execution_context(task, ctx, blocking=blocking)

        return models

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
