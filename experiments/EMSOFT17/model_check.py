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
from taskchain import model as tc_model
from taskchain import parser 

options.parser.add_argument('--input', type=str, required=True,
        help="Input file.")
options.parser.add_argument('--output', type=str, required=True,
        help="output file.")

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    p = parser.Graphml()
    m = p.model_from_file(options.get_opt('input'))
    assert(m.check())
    m.write_dot(options.get_opt('output'))
