#!/usr/bin/env python
import matplotlib.pyplot as pyplot
import matplotlib

import numpy as np
import argparse
import csv

parser = argparse.ArgumentParser(description='Plot scatter graph of WCRT results.')
parser.add_argument('file', metavar='csv_file', type=str, 
        help='csv file to be processed')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')
parser.add_argument('--xtask', default='T1b', type=str,
        help='Name of path used on x axis')
parser.add_argument('--ytask', default='T1a', type=str,
        help='Name of path used on y axis')

args = parser.parse_args()

def parse_results(filename):
    results = list()
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=args.delimiter)
        for row in reader:
            x = int(row[args.xtask])
            y = int(row[args.ytask])
            
            results.append((x,y))

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
    vals, counts = unique2d(results)
    x, y = zip(*vals)

    return (x, y, counts)

results = parse_results(args.file)
x,y,counts = prepare_results(results)

pyplot.scatter(x, y, s=counts)
p = min(max(x), max(y))
pyplot.plot([0,p],[0,p],color='r')
pyplot.show()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
