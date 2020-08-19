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

from pycpa import options
from pycpa import util
from pycpa import model
from pycpa import propagation

logger = logging.getLogger(__name__)

class Taskchain (object):
    """ A Taskchain models a chain of tasks in which no propagation of event models is required """

    def __init__(self, name=None, tasks=None):
        if tasks is not None:
            self.tasks = tasks
            self.__create_chain(tasks)
        else:
            self.tasks = list()

        # # create backlink to this chain from its last task
        self.tasks[-1].chain = self

        # # Name of Taskchain
        self.name = name

    def resource(self):
        # all tasks have the same resource
        return self.tasks[0].resource

    def __create_chain(self, tasks):
        """ linking all tasks along the chain"""
        assert len(tasks) > 0
        if len(tasks) == 1:
            return  # This is a fake path with just one task

    def __repr__(self):
        """ Return str representation """
        # return str(self.name)
        s = str(self.name) + ": "
        for c in self.tasks:
            s += " -> " + str(c)
        return s

class SchedulingContext (object):
    def __init__(self, name):
        # identifier
        self.name = name
        self.priority = 1

    def get_scheduling_parameter(self, task):
        return self.priority

class ExecutionContext (object):
    def __init__(self, name):
        # identifier
        self.name = name

class ResourceModel (object):
    """ Stores model (extended task graph) for a single resource. """
    def __init__(self, name):
        self.name = name

        self.tasks            = set()  # set of tasks
        self.junctions        = set()  # set of junctions
        self.juncinputs       = dict()  # set of input sources for junctions
        self.junclinks        = dict()  # links from junctions to tasks
        self.exec_ctxs        = list()  # set of execution contexts
        self.sched_ctxs       = list()  # set of scheduling contexts
#        self.tasklinks_strong = dict() # set of strong precedence relations (arcs in task graph)
        self.tasklinks        = dict() # set of precedence relations (arcs in task graph)
        self.allocations      = dict() # arcs between tasks and execution context
        self.mappings         = dict() # edges between tasks and scheduling contexts

    def add_task(self, t):
        assert(isinstance(t, model.Task))
        self.tasks.add(t)
        self.tasklinks[t] = set()
        self.junclinks[t] = None
        return t

    def add_junction(self, j):
        assert(isinstance(j, model.Junction))
        self.junctions.add(j)
        self.juncinputs[j] = set()
        return j

    def connect_junction(self, t, j):
        assert(isinstance(t, model.Task))
        assert(isinstance(j, model.Junction))

        self.juncinputs[j].add(t)

    def link_junction(self, j, t):
        assert(isinstance(t, model.Task))
        assert(isinstance(j, model.Junction))
        assert not self.junclinks[t]

        self.junclinks[t] = j

    def add_scheduling_context(self, s):
        assert(isinstance(s, SchedulingContext))
        self.sched_ctxs.append(s)
        return s

    def add_execution_context(self, e):
        assert(isinstance(e, ExecutionContext))
        self.exec_ctxs.append(e)
        return e

    def link_tasks(self, src, dst):
        assert(src in self.tasks)
        assert(dst in self.tasks)
        self.tasklinks[src].add(dst)

    def assign_execution_context(self, t, e, blocking=False):
        assert(t in self.tasks)
        assert(e in self.exec_ctxs)

        if t not in self.allocations:
            self.allocations[t] = dict()

        self.allocations[t][e] = blocking

    def assign_scheduling_context(self, t, s):
        assert(t not in self.mappings)
        assert(t in self.tasks)
        assert(s in self.sched_ctxs)

        self.mappings[t] = s
        t.scheduling_parameter = s.get_scheduling_parameter(t)

    def scheduled_tasks(self, s):
        tasks = set()
        for t in self.tasks:
            if self.mappings[t] is s:
                tasks.add(t)

        return tasks

    def allocating_tasks(self, e, only_released=False):
        tasks = set()
        for t in self.tasks:
            if t in self.allocations and e in self.allocations[t]:
                if not only_released:
                    tasks.add(t)
                elif self.allocations[t][e] is False:
                    tasks.add(t)

        return tasks

    def update_scheduling_parameters(self, s):
        for t in self.tasks:
            if self.mappings[t] is s:
                t.scheduling_parameter = s.get_scheduling_parameter(t)

    def predecessors(self, task, only_strong=False, recursive=False):
        predecessors = set()
        for t in self.tasklinks.keys():
            if task in self.tasklinks[t]:
                if not only_strong or self.is_strong_precedence(t, task):
                    predecessors.add(t)

        result = predecessors.copy()
        if recursive:
            for t in predecessors:
                result.update(self.predecessors(t, only_strong=only_strong, recursive=recursive))

        return result

    def successors(self, task, only_strong=False, recursive=False):
        successors = set()
        successors.update(self.tasklinks[task])

        if only_strong:
            result = set([s for s in successors if self.is_strong_precedence(task, s)])
        else:
            result = set(successors)

        if recursive:
            for t in successors:
                result.update(self.successors(t, only_strong=only_strong, recursive=recursive))

        return result

    def is_strong_precedence(self, src, dst):
        assert(dst in self.tasklinks[src])
        for ctx, blocking in self.allocations[src].items():
            if blocking and ctx in self.allocations[dst]:
                return True

        return False

    def get_mutex_interferers(self, task):
        interferers = set()
        for e in self.allocations[task]:
            interferers.update(self.allocating_tasks(e))

        interferers.remove(task)
        return interferers

    def get_blocking_segment(self, task, e):

        # perform forward search to find releasing task
        last_task = task
        while self.allocations[last_task][e]:
            for succ in self.successors(last_task):
                if e in self.allocations[succ]:
                    last_task = succ

        # perform backward search and add tasks to segment
        cur_task = last_task
        segment = [cur_task]
        done = False
        while not done:
            done = True
            for pred in self.predecessors(cur_task):
                if e in self.allocations[pred]:
                    if self.allocations[pred]:
                        done = False
                        segment.append(pred)
                        cur_task = pred
                        break

        segment.reverse()
        return segment

    def paths(self, root):
        paths = list()
        cur_path = [root]

        successors = self.successors(root)
        if len(successors) == 0:
            paths.append(cur_path)
        else:
            for t in successors:
                for sub_path in self.paths(t):
                    path = copy.copy(cur_path)
                    path += sub_path
                    paths.append(path)

        return paths

    def dfs(self, root):
        tasks = [root]
        for t in root.successors():
            tasks += self._dfs(t)

        return tasks

    def check(self):
        #####################
        # task graph checks #
        #####################

        # if a task blocks an execution context:
        #  - it must have exactly one successor that also blocks/releases the same execution context
        for t in self.tasks:
            assert t in self.allocations, 'no allocation for task %s' % t
            for e, blocking in self.allocations[t].items():
                if blocking:
                    strong_succ = 0
                    for succ in self.tasklinks[t]:
                        if e in self.allocations[succ]:
                            strong_succ += 1

                    assert strong_succ <= 1, \
                            "task %s has more than one strong successors" % t.name

                    assert strong_succ > 0, \
                            "task %s has does not release its execution context" % t.name


        # there is at most one strong predecessor (and only if there is no weak predecessor)
        for t in self.tasks:
            strong_pred = 0
            weak_pred = 0
            for pred in self.predecessors(t):
                if self.is_strong_precedence(pred, t):
                    strong_pred += 1
                else:
                    weak_pred += 1

            assert strong_pred <= 1, \
                   "task %s has multiple strong predecessors" % t.name
            assert weak_pred == 0 or strong_pred == 0, \
                   "task %s has strong and weak predecessors" % t.name

#            # if task has no predecessor it must have an input event model
#            if strong_pred + weak_pred == 0 and t.prev_task is None and self.junclinks[t] is None:
#                assert t.in_event_model is not None, "%s has not input event model" % t

        ###########################
        # allocation graph checks #
        ###########################

        for t in self.tasks:
            assert t in self.allocations and len(self.allocations[t]) > 0, \
                   "Task %s is not assigned to an execution context" % t.name

        for e in self.exec_ctxs:
            blocking_count = 0
            release_count = 0
            for ctxs in self.allocations.values():
                if e in ctxs:
                    if ctxs[e]:
                        blocking_count += 1
                    else:
                        release_count +=1

            assert blocking_count == 0 or release_count > 0, \
                   "execution context %s is never released" % e.name

        ########################
        # mapping graph checks #
        ########################
        
        for t in self.tasks:
            assert t in self.mappings and self.mappings[t] is not None, \
                   "Task %s is not assigned to a scheduling context" % t.name

        return True

    @staticmethod
    def write_dot(models, filename):
        convert_label = lambda label: label.replace('-', '_').replace(':', '')

        with open(filename, 'w+') as dotfile:
            dotfile.write("digraph g {\n")

            i = 0
            for m in models:
                m._write_dot(dotfile, "cluster%d" % i)
                i += 1

            # add inter-resource task links
            for m in models:
                for t in m.tasks:
                    if t.prev_task and isinstance(t, model.Task) and isinstance(t.prev_task, model.Task):
                        if t.prev_task.resource != t.resource:
                            dotfile.write("  %s -> %s" % (convert_label(t.prev_task.name), convert_label(t.name)))

            dotfile.write("}")

    def _write_dot(self, dotfile, name="cluster0"):

        convert_label = lambda label: label.replace('-', '_').replace(':', '')

        styles = { "sched" : "shape=note, colorscheme=set36, fillcolor=5, style=filled",
                   "exec"  : "shape=component, colorscheme=set36, fillcolor=4, style=filled",
                   "task"  : "style=filled, colorscheme=greys9, fillcolor=4",
                   "junction" : "style=filled,shape=diamond" }
        
        edge_styles = { "sched" : "arrowhead=dot, colorscheme=set36, color=5",
                        "exec"  : "arrowhead=halfopen, colorscheme=set36, color=4",
                        "task"  : "" }
        
        task_edge_styles = { "strong" : "",
                             "weak"   : "style=dashed, arrowhead=open" }
    
        dotfile.write("subgraph %s {\n" % name)
        dotfile.write("  label=\"%s\";" % convert_label(self.name))

        # add task nodes
        for t in self.tasks:
            uda = ',wcet=%d,bcet=%d' % (t.wcet, t.bcet)
            dotfile.write("  %s [%s%s];\n" % (convert_label(t.name), styles['task'], uda))

        # add junction nodes
        for j in self.junctions:
            dotfile.write("  %s [%s];\n" % (convert_label(j.name), styles['junction']))

        # add exec context nodes
        for e in self.exec_ctxs:
            dotfile.write("  %s [%s];\n" % (convert_label(e.name), styles['exec']))

        # add sched context nodes
        for s in self.sched_ctxs:
            uda = ',priority=%d' % s.priority
            dotfile.write("  %s [%s%s];\n" % (convert_label(s.name), styles['sched'], uda))

        # add task links
        for src in self.tasklinks.keys():
            for dst in self.tasklinks[src]:
                if self.is_strong_precedence(src, dst):
                    style = task_edge_styles["strong"]
                else:
                    style = task_edge_styles["weak"]

                dotfile.write("  %s -> %s [%s];\n" % (convert_label(src.name),
                    convert_label(dst.name),
                    style))

        # add junction links
        for t, j in self.junclinks.items():
            if j:
                style = task_edge_styles['weak']
                dotfile.write("  %s -> %s [%s];\n" % (convert_label(j.name),
                    convert_label(t.name),
                    style))

        # add junction inputs
        for j, ts in self.juncinputs.items():
            for t in ts:
                style = task_edge_styles['weak']
                dotfile.write("  %s -> %s [%s];\n" % (convert_label(t.name),
                    convert_label(j.name),
                    style))

        # add exec context allocations
        for t in self.allocations.keys():
            for ctx, blocking in self.allocations[t].items():
                target = convert_label(ctx.name)
                if blocking:
                    source = convert_label(t.name)
                    target = convert_label(ctx.name)
                else:
                    target = convert_label(t.name)
                    source = convert_label(ctx.name)

                dotfile.write("  %s -> %s [%s];\n" % (source,
                    target,
                    edge_styles["exec"]))

        # add sched context mappings
        for t in self.mappings.keys():
            dotfile.write("  %s -> %s [%s];\n" % (convert_label(t.name),
                convert_label(self.mappings[t].name),
                edge_styles["sched"]))

        dotfile.write("}")

class TaskchainResource (model.Resource):
    """ A Resource provides service to tasks. This Resource can contain task chains """

    def __init__(self, name=None, scheduler=None, **kwargs):
        """ CTOR """
        model.Resource.__init__(self, name, scheduler, **kwargs)

        self.model = None

        self.chains = set() # task chains to be analysed

    def build_from_model(self, model):
        self.model = model
        for t in self.model.tasks:
            t.chain = None
            assert t.bcet > 0
            assert t.wcet > 0
            t.bind_resource(self)
            if t in self.model.tasklinks:
                for ti in self.model.tasklinks[t]:
                    t.link_dependent_task(ti)

        # add junctions
        for j in self.model.junctions:
            for t in self.model.juncinputs[j]:
                t.link_dependent_task(j)

        for t, j in self.model.junclinks.items():
            if j is not None:
                j.link_dependent_task(t)

    def bind_taskchain(self, chain):
        for t in chain.tasks:
            if t.resource is not None:
                assert(t.resource is self)
            else:
                t.bind_resource(self)

        # skip analysis for all but the last task
        for t in chain.tasks[:-1]:
            t.skip_analysis = True
            t.OutEventModelClass = None

        chain.tasks[-1].skip_analysis = False
        chain.tasks[-1].OutEventModelClass = propagation.BusyWindowPropagationEventModel

        self.chains.add(chain)

        # NOTE how to use the same analysis result for every task in the chain

        return chain

    def create_taskchains(self, single=False):
        chained_tasks = set()
        for c in self.chains:
            chained_tasks.add(c.tasks)

        if single:
            # add remaining tasks as single-task "chains"
            for t in self.tasks - chained_tasks:
                self.bind_taskchain(Taskchain(t.name, [t]))
        else:
            # assumption: task graph has no joins -> task graph is a forest
            # task chains are paths from a root to a leaf
            roots = set()
            for t in self.tasks:
                if len(self.model.predecessors(t)) == 0:
                    roots.add(t)

            # perform a DFS
            paths = list()
            for r in roots - chained_tasks:
                paths += self.model.paths(r)

            for p in paths:
                self.bind_taskchain(Taskchain(p[0].name + "-" + p[-1].name, p))

        if not hasattr(self.scheduler, 'accept_model'):
            logger.warning("Scheduler %s has no method accept_model()." % type(self.scheduler))
        elif not self.scheduler.accept_model(self.chains, self.model):
            raise NotImplementedError("Scheduler %s has rejected taskchain model." % type(self.scheduler))

        return self.chains

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
