#!/usr/bin/env python
import matplotlib.pyplot as pyplot
import matplotlib

import numpy as np
import argparse
import csv

from palettable.colorbrewer.sequential import GnBu_4 as Palette


parser = argparse.ArgumentParser(description='Print statistics of path latency results.')
parser.add_argument('file', metavar='csv_file', type=str,
        help='csv file to be processed')
parser.add_argument('--output', type=str,
        help='Output format/file')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')
parser.add_argument('--latencies', default=['lat'], type=str, nargs="+",
        help='Identifiers of the latency values')
parser.add_argument('--xpath', default='S1', type=str,
        help='Name of path used on x axis')
parser.add_argument('--ypath', default='S2', type=str,
        help='Name of path used on y axis')
parser.add_argument('--title', default=None, type=str)
parser.add_argument('--xlabel', default=None, type=str)
parser.add_argument('--ylabel', default=None, type=str)
parser.add_argument('--xlim', default=0, type=float,
        help='x-axis limit')
parser.add_argument('--ylim', default=0, type=float,
        help='y-axis limit')
parser.add_argument('--fontsize', default=20, type=int)
parser.add_argument('--markers', default=['s', 'o', 'v'], type=str)
parser.add_argument('--priority_cols', type=str, nargs='+', required=True)
parser.add_argument('--names', type=str, nargs="*")

args = parser.parse_args()

def parse_results(filename, identifier):
    results = dict()
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=args.delimiter)
        for row in reader:
            eid = ""
            for col in args.priority_cols:
                eid += row[col]

            lat = int(row[identifier])
            if lat == 0:
                continue

            if eid not in results:
                results[eid] = dict()
            
            if 'Path' in row:
                name = row['Path']
            else:
                name = row['Chain']
            
            if name == args.xpath:
                axis = 'x'
            elif name == args.ypath:
                axis = 'y'
            else:
                continue

            results[eid][axis] = lat

    return results

def unique2d(a):
    unique = set(a)
    points = list()
    counts = list()
    for v in unique:
        points.append(v)
        counts.append(30+a.count(v)/4)

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
for lat in args.latencies:
    results = parse_results(args.file, lat)
    x,y,counts = prepare_results(results)

    marker = pyplot.scatter(x, y, s=counts, c=colors[len(colors)-1-i], marker=args.markers[i], lw=0.5)
    # workaround for marker size in legend
    marker = pyplot.plot(float('nan'),float('nan'),ls='',label=args.names[i],marker=args.markers[i],ms=10,c=colors[len(colors)-1-i]) 
    legend.append(marker)
    i += 1

if args.ylim != 0:
    pyplot.ylim(ymin=0, ymax=args.ylim)
if args.xlim != 0:
    pyplot.xlim(xmin=0, xmax=args.xlim)

if args.names:
#    pyplot.legend((legend), (args.names), markerscale=0.5, scatterpoints=1, loc="upper right")
    pyplot.legend(loc="upper right", numpoints=1)

tmp, max_x = pyplot.xlim()
tmp, max_y = pyplot.ylim()

#pyplot.plot([0, 150], [150, 150], 'r')
#pyplot.plot([150, 150], [0, 150], 'r')

if args.title is not None:
    pyplot.title(args.title)

if args.xlabel is not None:
    pyplot.xlabel(args.xlabel)

if args.ylabel is not None:
    pyplot.ylabel(args.ylabel)

matplotlib.rcParams.update({'font.size': args.fontsize})
if args.output is not None:
    pyplot.tight_layout()
    pyplot.savefig(args.output)
else:
    pyplot.show()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
