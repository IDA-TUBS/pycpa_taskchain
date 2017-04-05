#!/usr/bin/env python
import matplotlib.pyplot as pyplot
import matplotlib

import numpy as np
import argparse
import csv

parser = argparse.ArgumentParser(description='Print statistics of path latency results.')
parser.add_argument('file', metavar='csv_file', type=str, 
        help='csv file to be processed')
parser.add_argument('--output', type=str,
        help='Output format/file')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')
parser.add_argument('--xlabel', default=None, type=str)
parser.add_argument('--ylabel', default='# cases', type=str)
parser.add_argument('--bins', default=20, type=int,
        help='Number of bins')
parser.add_argument('--log', action='store_true',
        help='Logarithmic scale')
parser.add_argument('--yticks', default=[30, 50, 70, 100, 600], type=int, nargs='+',
        help='Ticks on the y axis for logarithmic scale')
parser.add_argument('--xticks', default=list(), type=float, nargs='+',
        help='Ticks on the x axis')
parser.add_argument('--original', default='lat', type=str,
        help='Identifier of original value')
parser.add_argument('--improved', default='lat_sync', type=str,
        help='Identifier of improved value')
parser.add_argument('--paths', type=str, nargs='+', required=True,
        help='Paths to be compared')
parser.add_argument('--pathnames', type=str, nargs='+', required=True,
        help='Path names')
parser.add_argument('--priority_cols', type=str, nargs='+', required=True)
parser.add_argument('--relative', action='store_true',
        help='Use relative improvement')
parser.add_argument('--fontsize', default=20, type=int)

args = parser.parse_args()

def parse_results(filename):
    results = dict()
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=args.delimiter)
        for row in reader:
            eid = ""
            for col in args.priority_cols:
                eid += row[col]

            if eid not in results:
                results[eid] = dict()

            orig = int(row[args.original])
            impr = int(row[args.improved])

            if 'Path' in row:
                name = row['Path']
            else:
                name = row['Chain']
            
            if name not in args.paths:
                continue

            if orig == 0 or impr == 0:
                results[eid][name] = 0
            else:
                if args.relative:
                    results[eid][name] = float(impr)/float(orig)
                else:
                    results[eid][name] = orig-impr

    return results

def prepare_results(results):
    points = list()
    for p in args.paths:
        points.append(list())

    for e in results.keys():
        for i in range(len(args.paths)):
            p = args.paths[i]
            points[i].append(results[e][p])

    return points

results = parse_results(args.file)
x = prepare_results(results)

fig, ax = pyplot.subplots(nrows=1, ncols=1)

assert(len(args.pathnames) == len(args.paths))

ax.hist(x, args.bins, align='right', log=args.log, histtype='bar', label=args.pathnames)
if args.log:
    ax.set_yticks(args.yticks)
    ax.get_yaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())

if len(args.xticks) > 0:
    ax.set_xticks(args.xticks)

if args.xlabel is not None:
    pyplot.xlabel(args.xlabel, fontsize=args.fontsize)

if args.ylabel is not None:
    pyplot.ylabel(args.ylabel, fontsize=args.fontsize)

ax.legend(prop={'size': args.fontsize})
ax.xaxis.set_tick_params(labelsize=args.fontsize)
ax.yaxis.set_tick_params(labelsize=args.fontsize)
matplotlib.rcParams.update({'font.size': args.fontsize})

if args.output is not None:
    pyplot.tight_layout(pad=0.5)
    pyplot.savefig(args.output)
else:
    pyplot.show()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
