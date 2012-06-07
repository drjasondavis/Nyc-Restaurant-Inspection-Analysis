import os
import sys

PICKLE_DIR = 'pickle'
DATA_DIR = 'data'

def txt_filename(f):
    return "%s/%s.txt" % (DATA_DIR, f)

def pkl_filename(f):
    return "%s/%s.pkl" % (PICKLE_DIR, f)

def setup_pickle_dirs():
    os.mkdir(PICKLE_DIR)
    os.mkdir('%s/%s' % (PICKLE_DIR, 'ratings'))
