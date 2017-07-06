#!/usr/bin/env python

import csv
import argparse

parser = argparse.ArgumentParser(description='Merge result files.')
parser.add_argument('--inputs', type=str,  nargs='+', required=True,
        help='Input files to be merged.')
parser.add_argument('--output', type=str,  required=True,
        help='Output file.')
parser.add_argument('--from_first', type=str, nargs='+', required=True,
        help='Column from first file.')
parser.add_argument('--from_second', type=str, nargs='+', required=True,
        help='Column from second file.')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')

args = parser.parse_args()

first  = args.inputs[0]
second = args.inputs[1]

def match_rows(row1, row2):
    for col in row1:
        skip = False
        for c in args.from_second:
            if c == col:
                skip = True
                break

        for c in args.from_first:
            if c == col:
                skip = True
                break

        if not skip:
            if row1[col] != row2[col]:
                return False

    return True

rows2 = list()
with open(second, 'r') as secondfile:
    reader = csv.DictReader(secondfile, delimiter=args.delimiter)
    for row in reader:
        rows2.append(row)

with open(first, 'r') as firstfile:
    reader = csv.DictReader(firstfile, delimiter=args.delimiter)

    fieldnames = reader.fieldnames
    with open(args.output, 'w') as outfile:
        writer = csv.DictWriter(outfile, delimiter=args.delimiter, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            for row2 in rows2:
                if match_rows(row, row2):
                    new_row = row.copy()
                    for col in args.from_second:
                        new_row[col] = row2[col]
                    writer.writerow(new_row)
                    rows2.remove(row2)
                    break
