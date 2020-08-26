#!/usr/bin/env python
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

from pycpa import options
from taskchain import model
from taskchain import benchmark
from taskchain import parser

import math
import csv

options.parser.add_argument('outpath', type=str,
        help="output path")
options.parser.add_argument('--nassign', type=int, default=10,
        help="number of random priority assignment per setup")
options.parser.add_argument('--offset', type=int, default=0,
        help="start at id")
options.parser.add_argument('--inherit', action='store_true',
        help="use priority inheritance")

def write_header(filename):
    header = ["Index", "Length", "Number", "Nesting", "Sharing", "Branching", "Load", "Inherit"]

    with open(filename, "w") as csvfile:
        writer = csv.writer(csvfile, delimiter='\t')
        writer.writerow(header)

def write_settings(filename, m, length, number, nesting_depth, sharing_level, branching_level, inherit, load):
    with open(filename, "a") as csvfile:
        writer = csv.writer(csvfile, delimiter='\t')

        row = [m.name,
               length,
               number,
               nesting_depth,
               sharing_level,
               branching_level,
               load,
               inherit]

        writer.writerow(row)

if __name__ == "__main__":
    # init pycpa and trigger command line parsing
    options.init_pycpa()

    outfile = "%s/settings.csv" % options.get_opt("outpath")
    write_header(outfile)

    index = 1 + options.get_opt('offset')
    for length in [13, 9, 5]:
        for number in [2, 4, 8]:
            for nesting_depth in range(0, min(3, 1+int(math.floor(length/2)))):
                for sharing_level in range(0, 3):
                    for branching_level in range(1, min(number+1, 5)):
                        g = benchmark.Generator(length=length, number=number, nesting_depth=nesting_depth,
                                sharing_level=sharing_level, branching_level=branching_level, inherit=options.get_opt('inherit'))
                        m = g.random_model()
                        g.random_activation(m, min_period=1000, max_period=10000, rel_jitter=0.1)
                        assert(m.check())

                        for load in [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98]:
                            # set WCETs randomly such that they generate the desired load
                            g.random_wcet(m, load=load, rel_jitter=0.1)

                            for n in range(options.get_opt('nassign')):
                                g.random_priorities(m)

                                m.name=str(index)
                                # write settings and graphml
                                write_settings(filename=outfile, m=m, sharing_level=sharing_level, nesting_depth=nesting_depth,
                                        branching_level=branching_level, length=length, number=number,
                                        inherit=options.get_opt('inherit'), load=g.calculate_load(m))
                                parser.Graphml.model_to_file(m, filename='%s/model-%s.graphml' %(options.get_opt('outpath'), m.name))
                                model.ResourceModel.write_dot([m], filename='%s/model-%s.dot' %(options.get_opt('outpath'), m.name))
                                index += 1
