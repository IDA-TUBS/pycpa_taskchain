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
from eval import usecase

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser(description='Print statistics.')
parser.add_argument('folder', type=str,
        help="Folder containing the subfolders with different analysis results in separate results.csv files.")
parser.add_argument('--xlabel', type=str)
parser.add_argument('--ylabel', type=str)
parser.add_argument('--output', default=None, required=False,
                        help='save plot to given file')

args = parser.parse_args()

if __name__ == "__main__":
    data = usecase.Data(folder=args.folder)
    data.process()
    df = data.unpivot()

    sns.set(style="darkgrid", palette="dark")
    g = sns.catplot(x='variable', y='value', data=df, kind='box', color='lightgray',
                    width=0.3,
                    showfliers=False,
                    linewidth=2)
    sns.swarmplot(x='variable', y='value', hue='Path', data=df, ax=g.ax,
                  size=7,
                  dodge=True)
    sns.despine(left=True)

    if args.xlabel:
        g.ax.set_xlabel(args.xlabel)

    if args.ylabel:
        g.ax.set_xlabel(args.ylabel)

    if args.output:
        plt.savefig(output, bbox_inches='tight')
    else:
        plt.show()
