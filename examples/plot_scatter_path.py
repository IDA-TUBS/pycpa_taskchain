#!/usr/bin/env python
import matplotlib.pyplot as pyplot
import matplotlib

import numpy as np
import argparse
import csv

parser = argparse.ArgumentParser(description='Print statistics of path latency results.')
parser.add_argument('file', metavar='csv_file', type=str, 
        help='csv file to be processed')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')
parser.add_argument('--original', default='lat1', type=str,
        help='Identifier of original value')
parser.add_argument('--improved', default='lat2', type=str,
        help='Identifier of improved value')
parser.add_argument('--xpath', default='S1', type=str,
        help='Name of path used on x axis')
parser.add_argument('--ypath', default='S2', type=str,
        help='Name of path used on y axis')
parser.add_argument('--relative', action='store_true',
        help='Use relative improvement')

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
            
            if row['Path'] == args.xpath:
                axis = 'x'
            elif row['Path'] == args.ypath:
                axis = 'y'
            else:
                continue

            if orig == 0 or impr == 0:
                results[eid][axis] = 0
            else:
                if args.relative:
                    results[eid][axis] = float(orig-impr)/float(orig)
                else:
                    results[eid][axis] = orig-impr

    return results

def unique2d(a):
    unique = set(a)
    points = list()
    counts = list()
    for v in unique:
        points.append(v)
        counts.append(10+a.count(v))

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

results = parse_results(args.file)
x,y,counts = prepare_results(results)

pyplot.scatter(x, y, s=counts)
pyplot.show()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
