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

parser = argparse.ArgumentParser(description='Print statistics.')
parser.add_argument('folder', type=str,
        help="Folder containing the subfolders with different analysis results in separate results.csv files.")

args = parser.parse_args()

if __name__ == "__main__":
    data = generated.LatencyData(folder=args.folder)
    data.filter_out(column='Branching', value=3)

    data.process()

    print(data.data_frame().head())

    df = data.data_frame()
    print("\nOverall best/worst rating:")
    print(df.select_dtypes(include=[bool]).sum())

    df = data.data_frame()[data.improvcolumns]
    print("\nOverall improvement statistics:")
    print(df.describe())


    # Schedulability results
    print('\n')
    data = generated.SchedulabilityData(folder=args.folder)
    data.filter_out(column='Branching', value=3)
    df = data.data_frame()
    print(df.head())

    print("\nAnalysis time statistics:")
    print(data.timedata().describe())

    print("\nSchedulability statistics:")
    print(data.crosscatlong())
