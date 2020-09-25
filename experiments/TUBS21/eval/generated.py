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
from pandas.api.types import CategoricalDtype

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

    def filter_out(self, column, value):
        df = self.dataframe
        filt = df[column].map(lambda x: x != value)
        self.dataframe = df[filt]


class SchedulabilityData(object):
    def __init__(self, csvfiles=None, folder=None):
        assert csvfiles or folder
        if folder:
            self.csvfiles = self.find_csvfiles(folder)
        else:
            self.csvfiles = csvfiles

        self.dataframe = None
        self.catcols = set()
        self.timecols = set()
        self.ignorecols = ['filename', 'Inherit']

        self.parse_and_combine()

    def find_csvfiles(self, folder):
        csvfiles = []
        for root, dirs, files in os.walk(folder):
            for d in dirs:
                for x, y, files in os.walk(folder+'/'+d):
                    if 'schedulability.csv' in files:
                        csvfiles.append('%s/%s/schedulability.csv' % (folder, d))

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
                if not self.catcols:
                    self.catcols = set(self.dataframe.columns).symmetric_difference(df.columns)
                else:
                    self.catcols |= (set(df.columns)-{'Time'}) - set(self.dataframe.columns)

                # automatically merges on the intersection of column names
                on = set(self.dataframe.columns) & set(df.columns) - {'Time'}
                l_suffix = '_%s' % list(set(self.dataframe.columns) & self.catcols)[0]
                r_suffix = '_%s' % list((set(df.columns) - {'Time'}) & self.catcols)[0]

                if 'Time' in set(self.dataframe.columns):
                    self.dataframe = self.dataframe.rename(columns={'Time' : 'Time%s' % l_suffix})
                df = df.rename(columns={'Time' : 'Time%s' % r_suffix})
                self.timecols |= {'Time%s' % l_suffix, 'Time%s' % r_suffix}
                self.dataframe = self.dataframe.merge(df, on=list(on), how='outer', validate='one_to_one')

        if self.dataframe is not None:
            cattype = CategoricalDtype(categories=['SCHED', 'UNSCHED', 'TIMEOUT'], ordered=True)
            for c in self.catcols:
                self.dataframe[c] = self.dataframe[c].astype(cattype)

            self.dataframe = self.dataframe.drop(self.ignorecols, axis=1)
            self.dataframe = self.dataframe.set_index('Index')

    def unpivot_time(self):
        df = None
        for c in self.catcols:
            melted = pd.melt(self.dataframe, value_vars=c, id_vars='Time_%s' % c,
                             value_name="Result",
                             var_name="Analysis") \
                       .rename(columns={'Time_%s'%c: 'Time'})
            if df is None:
                df = melted
            else:
                df = df.append(melted, ignore_index=True)

        return df

    def unpivot_cat(self):
        return pd.melt(self.dataframe, value_vars=self.catcols, var_name='Analysis', value_name='Result')

    def unpivot(self):
        return pd.melt(self.dataframe, id_vars=list(set(self.dataframe.columns)-self.timecols-self.catcols),
                                       value_vars=self.catcols,
                                       var_name='Analysis',
                                       value_name='Result')

    def timedata(self):
        return self.dataframe[self.timecols]

    def catdata(self):
        return self.dataframe[self.catcols]

    def scheddata(self, columns):
        total = len(self.dataframe.index)
        df = self.unpivot()

        if isinstance(columns, list):
            columns = ['Load', 'Analysis'] + columns
        else:
            columns = ['Load', 'Analysis', columns]

        rows = []
        for c in columns:
            rows.append(df[c])

        df = pd.crosstab(rows, df['Result'])
        df['Schedulability'] = df['SCHED'] / (df['SCHED'] + df['UNSCHED'] + df['TIMEOUT'])

        print((df['SCHED'] + df['UNSCHED'] + df['TIMEOUT']).describe())

        return df['Schedulability'].reset_index()

    def crosscatlong(self):
        df = self.unpivot_cat()
        return pd.melt(pd.crosstab(df['Analysis'], df['Result']).reset_index(), id_vars='Analysis')

    def data_frame(self):
        return self.dataframe

    def filter_out(self, column, value):
        df = self.dataframe
        filt = df[column].map(lambda x: x != value)
        self.dataframe = df[filt]
