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
from pandas.api.types import CategoricalDtype

parser = argparse.ArgumentParser(description='Print statistics.')
parser.add_argument('folders', type=str, nargs='+',
        help="Folder containing the subfolders with different analysis results in separate results.csv files.")
parser.add_argument('--width',  type=float, default=10)
parser.add_argument('--height', type=float, default=4)
parser.add_argument('--titles', type=str, nargs='*', default=None)
parser.add_argument('--order', type=str, nargs='*', default=list())
parser.add_argument('--xlabel', type=str, default=None)
parser.add_argument('--ylabel', type=str)
parser.add_argument('--output', default=None, required=False,
                        help='save plot to given file')

args = parser.parse_args()

if __name__ == "__main__":
    sns.set(style="darkgrid", palette="muted")
    cattype = CategoricalDtype(categories=['SCHED', 'UNSCHED', 'TIMEOUT'], ordered=True)

    df = []
    for folder in args.folders:
        data = generated.SchedulabilityData(folder=folder)
        data.filter_out('Branching', value=3)
        df.append(data.unpivot_time())
        df[-1]['Result'] = df[-1]['Result'].astype(cattype)
        if args.order:
            df[-1]['Analysis'] = df[-1]['Analysis'].astype(CategoricalDtype(categories=args.order, ordered=True))

    fig, axes = plt.subplots(1, len(args.folders), sharey=True, figsize=(args.width,args.height))
    if len(args.folders) == 1:
        plots = [(axes, df[0], None)]
    elif args.titles:
        assert len(args.titles) == len(args.folders)
        plots = zip(axes, df, args.titles)
    else:
        plots = zip(axes, df, [None for x in axes])

    first = True
    for ax, df, title in plots:
        sns.boxplot(y='Analysis', x='Time', data=df.mask(df['Result']=='TIMEOUT'),
                        hue='Result', ax=ax,
                        linewidth=1,
                        fliersize=1,
                        width=0.7)

        ax.get_legend().remove()

        if first:
            ax.set_ylabel(args.ylabel)
            first = False
        else:
            ax.set_ylabel(None)

        ax.set_xlabel(args.xlabel)

        if title is not None:
            ax.set_title(title)

    ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1))


    sns.despine(left=True)

    if args.output:
        plt.savefig(args.output, bbox_inches='tight')
    else:
        plt.show()
