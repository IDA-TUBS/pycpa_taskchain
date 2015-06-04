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
        num_failed = 0
        num_worse = 0
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
            
            l_old = dict()
            l_new = dict()
            l_old[0] = int(row['lat1a'])
            l_new[0] = int(row['lat1b'])
            l_old[1] = int(row['lat2a'])
            l_new[1] = int(row['lat2b'])
            l_old[2] = int(row['lat3a'])
            l_new[2] = int(row['lat3b'])
            l_old[3] = int(row['lat4a'])
            l_new[3] = int(row['lat4b'])
            l_old[4] = int(row['lat5a'])
            l_new[4] = int(row['lat5b'])

            if l_old[0] == 0:
                num_failed += 1

            for n in range(0, 5):
                if l_old[n] < l_new[n]:
                    num_worse += 1
                    worse_inst.add(inst)
                    continue

            num += 1

        print("Path Results Statistics for '%s':" % pathname)
        print("#Experiments:      %d" % num)
        print("# failed:         %d times" % num_failed)
        print("# worse:          %d times" % num_worse)

        return worst_inst

worse_inst = print_stats(args.file, "S1")
print("")
worse_inst.update(print_stats(args.file, "S2"))

print("\nInstances that resulted in worse latency:")
for inst in worse_inst:
    print(inst)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
