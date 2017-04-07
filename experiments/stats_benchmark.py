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
parser.add_argument('--wanted_load', type=str, nargs='+', required=False)
parser.add_argument('--wanted_length', type=str, nargs='+', required=False)
parser.add_argument('--wanted_number', type=str, nargs='+', required=False)
parser.add_argument('--wanted_nesting', type=str, nargs='+', required=False)
parser.add_argument('--wanted_sharing', type=str, nargs='+', required=False)
parser.add_argument('--print_less_than', default=None, type=int)

args = parser.parse_args()


def get_subfield(field, param, last=False):
    if param not in field:
        field[param] = dict()
        if last:
            field[param]['total']  = 0
            field[param]['good']   = 0  # schedulable / (total-good-failed) = unschedulable
            field[param]['failed'] = 0  # too may recursions

    return field[param]

def read_data(combinations):
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

                    if param == 'Load':
                        if args.wanted_load is not None:
                            if row[param] not in args.wanted_load:
                                break

                    if param == 'Length':
                        if args.wanted_length is not None:
                            if row[param] not in args.wanted_length:
                                break

                    if param == 'Number':
                        if args.wanted_number is not None:
                            if row[param] not in args.wanted_number:
                                break

                    if param == 'Nesting':
                        if args.wanted_nesting is not None:
                            if row[param] not in args.wanted_nesting:
                                break

                    if param == 'Sharing':
                        if args.wanted_sharing is not None:
                            if row[param] not in args.wanted_sharing:
                                break

                    field = get_subfield(field, row[param], last=last)

                    if last:
                        field['total'] += 1

                        if row['Schedulable'] == 'True':
                            field['good'] += 1
                            assert(row['MaxRecur'] == 'False')
                        elif row['MaxRecur'] == 'True':
                            field['failed'] += 1

    return combinations

def add_wanted_recursive(field, params):
    last = False
    param = params[0]
    if len(params) == 1:
        last = True
    else:
        new_params = params[1:]

    if param == 'Load':
        if args.wanted_load is not None:
            for load in args.wanted_load:
                get_subfield(field, load, last=last)

    if param == 'Length':
        if args.wanted_length is not None:
            for length in args.wanted_length:
                get_subfield(field, length, last=last)

    if param == 'Number':
        if args.wanted_number is not None:
            for number in args.wanted_number:
                get_subfield(field, number, last=last)

    if param == 'Nesting':
        if args.wanted_nesting is not None:
            for nesting in args.wanted_nesting:
                get_subfield(field, nesting, last=last)

    if param == 'Sharing':
        if args.wanted_sharing is not None:
            for sharing in args.wanted_sharing:
                get_subfield(field, sharing, last=last)

    if not last:
        for f in field:
            add_wanted_recursive(field[f], new_params)

    return field

def print_recursive(field, params):
    if 'total' in field:
        if args.print_less_than is not None:
            if field['total'] >= args.print_less_than:
                return
        print("%s:\t total: %d\t good: %d\t failed: %d" % (' '.join(params), field['total'], field['good'], field['failed']))
    else:
        for f in field:
            new_params = params + [f]
            print_recursive(field[f], new_params)

data = dict()
data = add_wanted_recursive(data, args.parameters)
data = read_data(data)

print("%s" % ' '.join(args.parameters))
print_recursive(data, list())

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
