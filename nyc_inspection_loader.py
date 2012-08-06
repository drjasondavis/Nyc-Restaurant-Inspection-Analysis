import csv
import random
import sys
import os

import numpy
import time
import datetime

import matplotlib.mlab as mlab
import matplotlib.pyplot as plt

from helper import *

class NycInspectionLoader:

    def load_and_pkl_csv(self, f):
        data = mlab.csv2rec(txt_filename(f))
        data.dump(pkl_filename(f))
        return data

    def load(self):
        load_data = None
        if os.path.exists('pickle'):
            print >> sys.stderr, "Loading nyc inspection results from pickled data"
            load_data = lambda x: numpy.load(pkl_filename(x))
        else:
            print >> sys.stderr, "Loadin nyc inspection results from raw csv data"
            os.mkdir('pickle')
            load_data = load_and_pkl_csv

        files = ['WebExtract', 'Cuisine']
        self.data_sets = {}
        for f in files:
            self.data_sets[f] = load_data(f)

    def filter_before(self, year):
        # remove values before year
        indexes = numpy.where(self.data_sets['WebExtract']['inspdate'] >= datetime.datetime(year, 1, 1))
        self.data_sets['WebExtract'] = self.data_sets['WebExtract'][indexes]

    def filter_by_region(self, region_no):
        indexes = numpy.where(self.data_sets['WebExtract']['boro'] == region_no)
        self.data_sets['WebExtract'] = self.data_sets['WebExtract'][indexes]
    
    def get_data(self):
        return self.data_sets

        
