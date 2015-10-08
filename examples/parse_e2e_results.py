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
        names = ["lat", "lat_async", "lat_sync", "lat_syncref"]
        num_failed = dict()
        num_worse = dict()
        latencies = dict()
        max_impr  = dict()

        for name in names:
            num_failed[name] = 0
            num_worse[name]  = 0
            max_impr[name]   = 0

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
            
            for name in names:
                latencies[name] = int(row[name])
                if latencies[name] == 0:
                    num_failed[name] += 1

            for i in zip(names[0:-1], names[1:]):
                if latencies[i[0]] > 0 and latencies[i[0]] < latencies[i[1]]:
                    num_worse[i[1]] += 1
                    worse_inst.add(inst)

            for name in names[1:]:
                if latencies[names[0]] == 0:
                    continue
                impr = latencies[names[0]]-latencies[name]
                if max_impr[name] < impr:
                    max_impr[name] = impr

            num += 1

        print("Path Results Statistics for '%s':" % pathname)
        print("#Experiments:      %d" % num)
        for name in names:
            print(name+":")
            print("  # failed:       %d times" % num_failed[name])
            print("  # worse:        %d times" % num_worse[name])
        for name in names[1:]:
            print("Maximum improvement for %s:  %d" % (name, max_impr[name]))

        return worst_inst

worse_inst = print_stats(args.file, "S1")
print("")
worse_inst.update(print_stats(args.file, "S2"))

print("\nInstances that resulted in worse latency:")
for inst in worse_inst:
    print(inst)

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
