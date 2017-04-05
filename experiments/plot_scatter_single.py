#!/usr/bin/env python
import matplotlib.pyplot as pyplot
import matplotlib

import numpy as np
import argparse
import csv

from palettable.colorbrewer.sequential import GnBu_4 as Palette

parser = argparse.ArgumentParser(description='Print statistics of path latency results.')
parser.add_argument('files', metavar='csv_file', type=str, nargs="+",
        help='csv file to be processed')
parser.add_argument('--output', type=str,
        help='Output format/file')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')
parser.add_argument('--original', default='lat', type=str,
        help='Identifier of original value')
parser.add_argument('--improved', default='lat_sync', type=str,
        help='Identifier of improved value')
parser.add_argument('--path', default='S2', type=str,
        help='Name of path used')
parser.add_argument('--title', default=None, type=str)
parser.add_argument('--xlabel', default=None, type=str)
parser.add_argument('--ylabel', default=None, type=str)
parser.add_argument('--xlim', default=0, type=float,
        help='x-axis limit')
parser.add_argument('--ylim', default=0, type=float,
        help='y-axis limit')
parser.add_argument('--fontsize', default=20, type=int)
parser.add_argument('--markers', default=['s', 'o', 'v'], type=str)
parser.add_argument('--names', type=str, nargs="*")

args = parser.parse_args()

def parse_results(filename):
    results = dict()
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=args.delimiter)
        for row in reader:
            eid = row['P1'] + row['P2'] + row['P3'] + row['P4'] + row['P5'] + row['P6']

            if eid not in results:
                results[eid] = dict()

            orig = int(row[args.original])
            impr = int(row[args.improved])
            
            if row['Path'] != args.path:
                continue

            results[eid]['x'] = orig
            results[eid]['y'] = impr

    return results

def unique2d(a):
    unique = set(a)
    points = list()
    counts = list()
    for v in unique:
        points.append(v)
        counts.append(5*a.count(v))

    return points, counts

def prepare_results(results):
    points = list()
    for e in results.keys():
        x = results[e]['x']
        y = results[e]['y']
        points.append((x,y))

    vals, counts = unique2d(points)
    x, y = zip(*vals)

    return (x, y, counts)

i = 0
colors = Palette.mpl_colors
legend = list()
for file in args.files:
    results = parse_results(file)
    x,y,counts = prepare_results(results)

    marker = pyplot.scatter(x, y, s=counts, c=colors[len(colors)-1-i], marker=args.markers[i], lw=0.5, alpha=0.8)
    # workaround for marker size in legend
    marker = pyplot.plot(float('nan'),float('nan'),ls='',label=args.names[i],marker=args.markers[i],ms=10,c=colors[len(colors)-1-i]) 
    legend.append(marker)
    i += 1

if args.ylim != 0:
    pyplot.ylim(ymin=0, ymax=args.ylim)
if args.xlim != 0:
    pyplot.xlim(xmin=0, xmax=args.xlim)

if args.names:
#    pyplot.legend((legend), (args.names), markerscale=0.5, scatterpoints=1, loc="lower right")
    pyplot.legend(loc="lower right", numpoints=1)

tmp, max_x = pyplot.xlim()
tmp, max_y = pyplot.ylim()
lim = max_x if max_x < max_y else max_y
linecolor=colors[1]
linecolor='0.6'
pyplot.plot([0, lim], [0, lim], color=linecolor)
pyplot.plot([0, lim], [0, lim*0.9], color=linecolor)
pyplot.plot([0, lim], [0, lim*0.8], color=linecolor)
pyplot.plot([0, lim], [0, lim*0.7], color=linecolor)
pyplot.plot([0, lim], [0, lim*0.6], color=linecolor)
pyplot.plot([0, lim], [0, lim*0.5], color=linecolor)

if args.title is not None:
    pyplot.title(args.title)

if args.xlabel is not None:
    pyplot.xlabel(args.xlabel)

if args.ylabel is not None:
    pyplot.ylabel(args.ylabel)

matplotlib.rcParams.update({'font.size': args.fontsize})
if args.output is not None:
    pyplot.savefig(args.output)
else:
    pyplot.show()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
