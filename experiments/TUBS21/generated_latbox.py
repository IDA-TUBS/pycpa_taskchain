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
from pandas.api.types import CategoricalDtype

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Print statistics.')
parser.add_argument('folder', type=str,
        help="Folder containing the subfolders with different analysis results in separate results.csv files.")
parser.add_argument('--xlabel', type=str)
parser.add_argument('--ylabel', type=str)
parser.add_argument('--width', type=float, default=7)
parser.add_argument('--height', type=float, default=4)
parser.add_argument('--strip', action='store_true')
parser.add_argument('--order', type=str, nargs='*', default=list())
parser.add_argument('--pathorder', type=str, nargs='*', default=list())
parser.add_argument('--pathnames', type=str, nargs='*', default=list())
parser.add_argument('--output', default=None, required=False,
                        help='save plot to given file')

args = parser.parse_args()

if __name__ == "__main__":
    data = generated.LatencyData(folder=args.folder)
    data.process()
    df = data.unpivot().dropna(axis=0)

    if args.order:
        df['variable'] = df['variable'].astype(CategoricalDtype(categories=args.order, ordered=True))

    if args.pathorder:
        df['Path'] = df['Path'].astype(CategoricalDtype(categories=args.pathorder, ordered=True))

    if args.pathnames:
        assert args.pathorder and len(args.pathorder) == len(args.pathnames)
        df['Path'] = df['Path'].cat.rename_categories(args.pathnames)

    sns.set(style="darkgrid", palette="dark")

    fig = plt.figure(figsize=(args.width, args.height))
    ax = fig.add_subplot()

    sns.catplot(x='variable', y='value', data=df, kind='box', color='lightgray',
                    width=0.3,
                    showfliers=not args.strip,
                    ax=ax,
                    linewidth=2)

    if args.strip:
        sns.stripplot(x='variable', y='value', hue='Path', data=df, ax=ax,
                      size=2,
                      dodge=True)

    sns.despine(left=True)

    if args.xlabel:
        ax.set_xlabel(args.xlabel)

    if args.ylabel:
        ax.set_ylabel(args.ylabel)

    if args.order and len(args.order) == 1:
        a, b = plt.xlim()
        plt.xlim(2*a, 2*b)

    if args.output:
        plt.savefig(args.output, bbox_inches='tight')
    else:
        plt.show()
