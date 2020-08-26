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

import csv
import os
import pandas as pd

class LatencyData(object):
    def __init__(self, csvfiles=None, folder=None):
        assert csvfiles or folder
        if folder:
            self.csvfiles = self.find_csvfiles(folder)
        else:
            self.csvfiles = csvfiles

        self.dataframe = None
        self.basecolumns = set()
        self.ignorecols = ['filename', 'Inherit']

        self.parse_and_combine()

    def find_csvfiles(self, folder):
        csvfiles = []
        for root, dirs, files in os.walk(folder):
            for d in dirs:
                for x, y, files in os.walk(folder+'/'+d):
                    if 'latency.csv' in files:
                        csvfiles.append('%s/%s/latency.csv' % (folder, d))

        return csvfiles

    def parse_and_combine(self):
        dataframes = []
        for csvfile in self.csvfiles:
            dataframes.append(pd.read_csv(csvfile, sep='\t', index_col=False))

        self.dataframe = None
        for df in dataframes:
            if self.dataframe is None:
                self.dataframe = df
            else:
                # automatically merges on the intersection of column names
                self.basecolumns |= set(self.dataframe.columns).symmetric_difference(df.columns)
                self.dataframe = self.dataframe.merge(df, how='outer', validate='one_to_one')

        self.dataframe = self.dataframe.drop(self.ignorecols, axis=1)
        self.dataframe = self.dataframe.set_index(['Path', 'Index'])

    def _proc_best_worst(self):
        # insert best/worst columns
        for c in self.basecolumns:
            best  = None
            worst = None
            for cc in self.basecolumns - {c}:
                if best is None:
                    best = self.dataframe[c].fillna(float('inf')) <= self.dataframe[cc].fillna(float('inf'))
                else:
                    best = best & (self.dataframe[c].fillna(float('inf')) <= self.dataframe[cc].fillna(float('inf')))

                if worst is None:
                    worst = self.dataframe[c].fillna(float('inf')) >= self.dataframe[cc].fillna(float('inf'))
                else:
                    worst = worst & (self.dataframe[c].fillna(float('inf')) >= self.dataframe[cc].fillna(float('inf')))

            self.dataframe['%s-best'%c] = best
            self.dataframe['%s-worst'%c] = worst

    def _proc_improv(self):
        self.improvcolumns = list()
        # insert best/worst columns
        for c in self.basecolumns:
            for cc in self.basecolumns - {c}:
                best = self.dataframe[c] < self.dataframe[cc]
                if best.any():
                    self.dataframe['%s/%s'%(c,cc)] = self.dataframe[c]/self.dataframe[cc]
                    self.improvcolumns.append('%s/%s'%(c,cc))

    def process(self):
        assert self.dataframe is not None
        assert len(self.dataframe.columns) > 1

        self._proc_best_worst()
        self._proc_improv()

    def data_frame_path(self, p):
        return self.dataframe.loc[p]

    def unpivot(self):
        df = self.dataframe.reset_index(level='Path')
        df = pd.melt(df, id_vars=['Path'], value_vars=self.improvcolumns)
        return df

    def paths(self):
        return set(self.dataframe.index.get_level_values('Path'))

    def data_frame(self):
        return self.dataframe
