#!/usr/bin/env python
import argparse
import csv

from pyplot_helper import barchart
from matplotlib import pyplot

from palettable.colorbrewer.qualitative import Paired_12 as Colors 

parser = argparse.ArgumentParser(description='Plot benchmark results.')
parser.add_argument('--inputs', type=str, required=True, nargs='+',
        help='Input files')
parser.add_argument('--output', type=str, 
        help='Output file')
parser.add_argument('--delimiter', default='\t', type=str,
        help='CSV delimiter')
parser.add_argument('--fontsize', default=20, type=int,
        help='Font size')
parser.add_argument('--colorshift', default=1, type=int)
parser.add_argument('--parameters', type=str, nargs='+', required=True,
        help='Parameters to evaluate')
parser.add_argument('--names', type=str, default=None, nargs="+",
        help='Names')
parser.add_argument('--filter_load', type=str, default=None, nargs='+')
parser.add_argument('--filter_length', type=str, default=None, nargs='+')
parser.add_argument('--filter_number', type=str, default=None, nargs='+')
parser.add_argument('--filter_nesting', type=str, default=None, nargs='+')
parser.add_argument('--filter_sharing', type=str, default=None, nargs='+')
parser.add_argument('--absolute', action='store_true')
parser.add_argument('--stackfailed', action='store_true')
parser.add_argument('--failed', action='store_true')

args = parser.parse_args()

charts = dict()
i = 0
for param in args.parameters:
    name = param
    if args.names is not None:
        name = args.names[i]

    ylabel = ""
    charts[param] = barchart.BarChart(ylabel=ylabel, xlabel=name,
            title="",
            width=1,
            rotation=0,
            colors=Colors.mpl_colors,
            colorshift=args.colorshift,
            xticksize=args.fontsize,
            labelsize=args.fontsize,
            legend_loc="upper right",
            legend_cols=len(args.parameters)+1,
            legend_anchor=(1,1.2),
            legendsize=args.fontsize)
    i += 1

def read_data(param):
    groups = dict()

    for filename in args.inputs:
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile, delimiter='\t')

            for row in reader:
                group = row[param]
                cat   = row['Load']
                if args.filter_load is not None:
                    if cat not in args.filter_load:
                        continue
                if args.filter_number is not None:
                    if row['Number'] not in args.filter_number:
                        continue
                if args.filter_length is not None:
                    if row['Length'] not in args.filter_length:
                        continue
                if args.filter_nesting is not None:
                    if row['Nesting'] not in args.filter_nesting:
                        continue
                if args.filter_sharing is not None:
                    if row['Sharing'] not in args.filter_sharing:
                        continue

                if group not in groups:
                    groups[group] = dict()

                if cat not in groups[group]:
                    groups[group][cat] = dict()
                    groups[group][cat]['total']  = 0
                    groups[group][cat]['good']   = 0  # schedulable / (total-good-failed) = unschedulable
                    groups[group][cat]['failed'] = 0  # too may recursions

                groups[group][cat]['total'] += 1
                if row['Schedulable'] == 'True':
                    groups[group][cat]['good'] += 1
                    assert(row['MaxRecur'] == 'False')
                elif row['MaxRecur'] == 'True':
                    groups[group][cat]['failed'] += 1

    return groups

fig, axes = pyplot.subplots(1, len(charts), figsize=(6*len(charts),5))
i = 0
for param in charts:
    data = read_data(param)

    for group in data:
        values = list()
        for cat in data[group]:

            if args.absolute:
                if args.stackfailed:
                    val = [data[group][cat]['failed'], data[group][cat]['good']]
                elif args.failed:
                    val = data[group][cat]['failed']
                else:
                    val = data[group][cat]['good']
            else:
                good   = data[group][cat]['good']
                total  = data[group][cat]['total']
                failed = data[group][cat]['failed']
                if args.stackfailed:
                    val = [failed * 100 / total, good * 100 / total]
                elif args.failed:
                    val = failed * 100 / total
                else:
                    val = good * 100 / total

            values.append((cat, val))

        charts[param].add_group_data(group, values)

    if args.filter_load is not None:
        for load in args.filter_load:
            charts[param].add_category(load, load +"% Load")
    else:
        charts[param].add_category("60", "60% Load")
        charts[param].add_category("80", "80% Load")
        charts[param].add_category("90", "90% Load")
        charts[param].add_category("95", "95% Load")
        charts[param].add_category("98", "98% Load")
        charts[param].add_category("99", "99% Load")
        charts[param].add_category("100", "100% Load")

    charts[param].plot(axes[i], stacked=False, sort=False)
    i += 1

for ax in axes:
    ax.set_yticks([20, 40, 60, 80, 100])
    ax.set_yticklabels(list())

axes[0].set_yticklabels(["20%", "40%", "60%", "80%", "100%"], fontsize=args.fontsize)

pyplot.rcParams.update({'font.size': args.fontsize})

# output
if args.output is not None:
#    fig.subplots_adjust(top=0.5, bottom=0.15)
    pyplot.tight_layout(rect=(0, -0.05, 1, 0.95))
    pyplot.savefig(args.output)
else:
    pyplot.show()

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
