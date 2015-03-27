#!/usr/bin/env python
import argparse
import csv

parser = argparse.ArgumentParser(description='Print statistics of path latency results.')
parser.add_argument('file', metavar='csv_file', type=str, 
        help='csv file to be processed')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')

args = parser.parse_args()

def print_stats(filename, pathname):
    with open(filename, 'r') as csvfile:
        reader = csv.DictReader(csvfile, delimiter=args.delimiter)
        num = 0
        a1_failed = 0
        a2_failed = 0
        a3_failed = 0
        a2_worse = 0
        a3_worse_a1 = 0
        a3_worse_a2 = 0
        a2_better = 0
        a3_better_a1 = 0
        a3_better_a2 = 0
        worst_inst = set()
        for row in reader:
            if row['Path'] != pathname:
                continue

            inst = str([int(row['P1']),
                        int(row['P2']),
                        int(row['P3']),
                        int(row['P4']),
                        int(row['P5']),
                        int(row['P6'])])
            
            l1 = int(row['lat1'])
            l2 = int(row['lat2'])
            l3 = int(row['lat3'])

            if l1 == 0:
                a1_failed += 1
            if l2 == 0:
                a2_failed += 1
            if l3 == 0:
                a3_failed += 1

            if l1 > 0 and l2 > l1:
                a2_worse += 1
                worst_inst.add(inst)
            if l1 > 0 and l3 > l1:
                a3_worse_a1 += 1
                worst_inst.add(inst)
            if l2 > 0 and l3 > l2:
                a3_worse_a2 += 1
                worst_inst.add(inst)

            if l2 > 0 and l2 < l1:
                a2_better += 1
            if l3 > 0 and l3 < l1:
                a3_better_a1 += 1
            if l3 > 0 and l3 < l2:
                a3_better_a2 += 1

            num += 1

        print("Path Results Statistics for '%s':" % pathname)
        print("#Experiments:      %d" % num)
        print("A1 failed:         %d times" % a1_failed)
        print("A2 failed:         %d times" % a2_failed)
        print("A3 failed:         %d times" % a3_failed)
        print("A2 worse:          %d times" % a2_worse)
        print("A3 worse than A1:  %d times" % a3_worse_a1)
        print("A3 worse than A2:  %d times" % a3_worse_a2)
        print("A2 better:         %d times" % a2_better)
        print("A3 better than A1: %d times" % a3_better_a1)
        print("A3 better than A2: %d times" % a3_better_a2)

        return worst_inst

worse_inst = print_stats(args.file, "S1")
print("")
worse_inst.update(print_stats(args.file, "S2"))

print("\nInstances that resulted in worse latency:")
for inst in worse_inst:
    print(inst)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
