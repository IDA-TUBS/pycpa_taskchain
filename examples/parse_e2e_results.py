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

import argparse
import csv

parser = argparse.ArgumentParser(description='Print statistics of path latency results.')
parser.add_argument('file', metavar='csv_file', type=str, 
        help='csv file to be processed')
parser.add_argument('--paths', type=str,  nargs='+', 
        help='Paths/chains to be parsed.')
parser.add_argument('--experiments', type=str,  nargs='+', 
        help='Experiments to be compared.')
parser.add_argument('--worse_details', action='store_true', 
        help='Print details on worse results (compared to the first experiment).')
parser.add_argument('--better_details', action='store_true', 
        help='Print details on better results (compared to the first experiment).')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')

args = parser.parse_args()

def print_stats(filename, pathname, experiments, wdetails, bdetails):
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=args.delimiter)
        num = 0
        num_failed = dict()
        num_worse  = dict()
        num_better = dict()
        latencies  = dict()

        for e in experiments:
            num_failed[e] = 0
            num_worse[e]  = 0
            num_better[e]  = 0

        for row in reader:
            if row['Path'] != pathname:
                continue

            # heuristically filter out not relevant columns
            inst_cols = dict()
            for col in row.keys():
                lc_name = col.lower()
                if lc_name.startswith('lat'):
                    continue
                if lc_name.startswith('tc'):
                    continue
                if lc_name.startswith('async'):
                    continue
                if lc_name.startswith('sync'):
                    continue
                if lc_name == 'path' or lc_name == 'std' or lc_name == 'cpa':
                    continue

                inst_cols[col] = row[col]

            # compose instance string
            inst = ""
            for n, v in inst_cols.items():
                inst += "%s:%s " % (n, v)

            # collect latency results

            for e in experiments:
                latencies[e] = int(row[e])
                if latencies[e] == 0:
                    num_failed[e] += 1

            for e in experiments[1:]:
                if latencies[experiments[0]] > 0 and latencies[e] > 0 and latencies[experiments[0]] < latencies[e]:
                    num_worse[e] += 1

                    if wdetails is not None:
                        if inst not in wdetails:
                            wdetails[inst] = dict()
                        if pathname not in wdetails[inst]:
                            wdetails[inst][pathname] = dict()

                        wdetails[inst][pathname][experiments[0]] = latencies[experiments[0]]
                        wdetails[inst][pathname][e] = latencies[e]
                elif latencies[experiments[0]] > 0 and latencies[e] > 0 and latencies[experiments[0]] > latencies[e]:
                    num_better[e] += 1

                    if bdetails is not None:
                        if inst not in bdetails:
                            bdetails[inst] = dict()
                            bdetails[inst][pathname] = dict()
                        if pathname not in bdetails[inst]:
                            bdetails[inst][pathname] = dict()

                        bdetails[inst][pathname][experiments[0]] = latencies[experiments[0]]
                        bdetails[inst][pathname][e] = latencies[e]

            num += 1

        print("Path Results Statistics for '%s':" % pathname)
        print("#Experiments:      %d" % num)
        for e in experiments:
            print(e+":")
            print("  # failed:       %d times" % num_failed[e])
            print("  # worse:        %d times" % num_worse[e])
            print("  # better:       %d times" % num_better[e])

if __name__ == "__main__":

    assert(len(args.paths) >= 1)
    assert(len(args.experiments) >= 2)

    if args.worse_details:
        worse_details = dict()
    else:
        worse_details = None

    if args.better_details:
        better_details = dict()
    else:
        better_details = None

    for p in args.paths:
        print_stats(args.file, p, args.experiments, worse_details, better_details)

    if args.worse_details:
        print("\nInstances that resulted in worse latency:")
        for name, results in worse_details.items():
            print("%s: " % name)
            for path, experiments in results.items():
                print("  Path %s:" % (path))
                for e, lat in experiments.items():
                    print("    %s: %s" % (e, lat))

    if args.better_details:
        print("\nInstances that resulted in better latency:")
        for name, results in better_details.items():
            print("%s: " % name)
            for path, experiments in results.items():
                print("  Path %s:" % (path))
                for e, lat in experiments.items():
                    print("    %s: %s" % (e, lat))

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
