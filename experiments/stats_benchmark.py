#!/usr/bin/env python
import argparse
import csv

from pyplot_helper import barchart
from matplotlib import pyplot

from palettable.colorbrewer.qualitative import Set1_9 as Colors 

parser = argparse.ArgumentParser(description='Plot benchmark results.')
parser.add_argument('--inputs', type=str, required=True, nargs='+',
        help='Input files')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')
parser.add_argument('--parameters', type=str, nargs='+', required=True,
        help='Parameters to evaluate')

args = parser.parse_args()


def get_subfield(field, param, last=False):
    if param not in field:
        field[param] = dict()
        if last:
            field[param]['total']  = 0
            field[param]['good']   = 0  # schedulable / (total-good-failed) = unschedulable
            field[param]['failed'] = 0  # too may recursions

    return field[param]

def read_data():
    combinations = dict()
    for filename in args.inputs:
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')

            for row in reader:
                field = combinations
                for i in range(len(args.parameters)):
                    param = args.parameters[i]
                    last = False
                    if i == len(args.parameters)-1:
                        last = True

                    field = get_subfield(field, row[param], last=last)

                    if last:
                        field['total'] += 1

                        if row['Schedulable'] == 'True':
                            field['good'] += 1
                            assert(row['MaxRecur'] == 'False')
                        elif row['MaxRecur'] == 'True':
                            field['failed'] += 1

    return combinations

def print_recursive(field, params):
    if 'total' in field:
        print("%s:\t total: %d\t good: %d\t failed: %d" % (' '.join(params), field['total'], field['good'], field['failed']))
    else:
        for f in field:
            new_params = params + [f]
            print_recursive(field[f], new_params)

data = read_data()
print("%s" % ' '.join(args.parameters))
print_recursive(data, list())

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
