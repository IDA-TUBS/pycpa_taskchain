"""
| Copyright (C) 2015 Johannes Schlatow
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

logger = logging.getLogger(__name__)

class Taskchain (object):
    """ A Taskchain models a chain of tasks in which no propagation of event models is required """

    def __init__(self, name=None, tasks=None):
        if tasks is not None:
            self.tasks = tasks
            self.__create_chain(tasks)
        else:
            self.tasks = list()

        # # create backlink to this chain from the tasks
        # # so a task knows its Taskchain
        for t in self.tasks:
            t.chain = self

        # # Name of Taskchain
        self.name = name

    def __create_chain(self, tasks):
        """ linking all tasks along the chain"""
        assert len(tasks) > 0
        if len(tasks) == 1:
            return  # This is a fake path with just one task
        for i in zip(tasks[0:-1], tasks[1:]):
            assert(i[0].resource == i[1].resource)
            i[0].no_propagation = True

    def __repr__(self):
        """ Return str representation """
        # return str(self.name)
        s = str(self.name) + ": "
        for c in self.tasks:
            s += " -> " + str(c)
        return s


class TaskchainResource (model.Resource):
    """ A Resource provides service to tasks. This Resource can contain task chains """

    def __init__(self, name=None, scheduler=None, **kwargs):
        """ CTOR """
        model.Resource.__init__(self, name, scheduler, **kwargs)

        self.chains = set()

    def bind_taskchain(self, chain):
        self.chains.add(chain)

        # NOTE how to use the same analysis result for every task in the chain

        return chain

    def create_taskchains(self):
        # TODO automatically find and create task chains

        # add remaining tasks as single-task "chains"
        for t in self.tasks:
            if not hasattr(t, 'chain'):
                self.bind_taskchain(Taskchain(t.name, [t]))

        return self.chains

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
