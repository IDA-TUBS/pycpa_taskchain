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

parser = argparse.ArgumentParser(description='Print statistics.')
parser.add_argument('folder', type=str,
        help="Folder containing the subfolders with different analysis results in separate results.csv files.")

args = parser.parse_args()

if __name__ == "__main__":
    data = usecase.Data(folder=args.folder)

    data.process()

    print(data.data_frame().head())

    df = data.data_frame()
    print("\nOverall best/worst rating:")
    print(df.select_dtypes(include=[bool]).sum())

    df = data.data_frame()[data.improvcolumns]
    print("\nOverall improvement statistics:")
    print(df.describe())

    for p in data.paths():
        df = data.data_frame_path(p)
        print("\nPath %s - best/worst rating" % p)
        print(df.select_dtypes(include=[bool]).sum())
        df = df[data.improvcolumns]
        print("Path %s - improvement statistics" % p)
        print(df.describe())

