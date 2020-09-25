#!/usr/bin/env python
"""
| Copyright (C) 2020 Johannes Schlatow
| TU Braunschweig, Germany
| All rights reserved.
| See LICENSE file for copyright and license details.

:Authors:
         - Johannes Schlatow

Description
-----------

"""

import argparse
from eval import generated

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Print statistics.')
parser.add_argument('folder', type=str,
        help="Folder containing the subfolders with different analysis results in separate results.csv files.")
parser.add_argument('--xlabel', type=str)
parser.add_argument('--ylabel', type=str)
parser.add_argument('--width', type=float, default=4)
parser.add_argument('--height', type=float, default=3.5)
parser.add_argument('--row', type=str, default=None)
parser.add_argument('--col', type=str, default='Length')
parser.add_argument('--nolegend', action='store_true')
parser.add_argument('--output', default=None, required=False,
                        help='save plot to given file')

args = parser.parse_args()

if __name__ == "__main__":
    data = generated.SchedulabilityData(folder=args.folder)
    data.filter_out(column='Branching', value=3)
    if args.row:
        df = data.scheddata([args.row, args.col])
    else:
        df = data.scheddata(args.col)

    sns.set(style="darkgrid", palette="dark")

    g = sns.FacetGrid(df, col=args.col, height=args.height, aspect=args.width/args.height,row=args.row, hue='Analysis', margin_titles=True)
    if args.nolegend:
        g = (g.map(plt.plot, 'Load', 'Schedulability',marker='.'))
    else:
        g = (g.map(plt.plot, 'Load', 'Schedulability',marker='.').add_legend(loc='lower center', ncol=4))

    sns.despine(left=True)

    if args.xlabel:
        for ax in g.axes[0]:
            ax.set_xlabel(args.xlabel)

    if args.ylabel:
        for ax in g.axes[0]:
            ax.set_ylabel(args.ylabel)

    if args.output:
        g.fig.subplots_adjust(bottom=0.32)
        plt.savefig(args.output, bbox_inches='tight')
    else:
        plt.show()
