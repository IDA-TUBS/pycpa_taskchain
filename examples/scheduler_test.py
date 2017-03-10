#!/usr/bin/env python
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

from pycpa import options
from pycpa import analysis
from pycpa import model
from taskchain import model as tc_model
from taskchain import schedulers as tc_schedulers
from taskchain import parser 

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    p = parser.Graphml()
    m = p.model_from_file("test.graphml")
    assert(m.check())
    m.write_dot('test.dot')

    s = model.System("System")
    r = s.bind_resource(tc_model.TaskchainResource("R1", scheduler=tc_schedulers.SPPScheduler()))
    r.build_from_model(m)
    r.create_taskchains()

    analysis.analyze_system(s)
