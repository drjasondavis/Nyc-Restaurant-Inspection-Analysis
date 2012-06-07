import os
import sys
import re

import json

import dateutil.parser
import urllib
import urllib2
import pickle
import numpy
import matplotlib.mlab as mlab

from nyc_inspection_loader import NycInspectionLoader
from helper import *

REGION = 'Manhattan'
QUERY = 'Restaurants'
NUM_TOP_PLACES = 1000
PICKLE_DIR = 'pickle'
USER_AGENT = 'nyc-restaurant-inspection-analyzer'

reg = re.compile('<span class="value-title" title="(\d)"></span>\s+</div>\s+<em class="dtreviewed smaller">(\d+/\d+/\d+) <span', re.MULTILINE)
search_reg = re.compile('<a id="bizTitleLink\d+" href="([^"?#]+)[^"]*">\d+\.')


def write_data(name, data):
    pickle.dump(data, open(pkl_filename(name), 'wb'))

def load_data(name):
    return pickle.load(open(pkl_filename(name), 'rb'))

def get_search_results(desc, loc, start = 0):
    url = 'http://www.yelp.com/search?find_desc=%s&find_loc=%s&start=%s' % (urllib.quote(desc), loc, start)
    print 'url = %s' % url
    response = urllib2.urlopen(urllib2.Request(url, None, {'User-Agent': USER_AGENT}))
    data = response.read()
    matches = search_reg.findall(data)
    return matches
    
def get_top_places():
    limit = 10
    results = []
    for offset in range(0, NUM_TOP_PLACES, limit):
        matches = get_search_results(QUERY, REGION, offset)
        for m in matches:
            results.append(re.sub('^/biz/', '', m))
    return results



"""
<span class="value-title" title="4"></span>
        </div>

                                                <em class="dtreviewed smaller">5/27/2012 <span class="value-title" title="2012-05-27"></span></em>
"""
def crawl_place(place_name):
    offset = 0
    reviews = []
    while(True):
        url = 'http://www.yelp.com/biz/%s?start=%d' % (place_name, offset)
        print 'Crawling biz: %s, offset: %s, url: %s' % (place_name, offset, url)
        response = urllib2.urlopen(urllib2.Request(url, None, {'User-Agent': USER_AGENT}))
        data = response.read()
        matches = reg.findall(data)
        if len(matches) == 0:
            break
        reviews = reviews + matches
        offset += 40
    write_data('ratings/%s' % place_name, reviews)
    return reviews

def crawl_all_places(places):
    for p in places:
        try:
            loc = 'ratings/%s' % p
            load_data(loc)
            print 'Data loaded from %s' % loc
        except: 
            crawl_place(p)
            print 'Data crawled for place: %s' % p

def print_top_places(places):
    for p in places:
        print p

def ratings_around_date(date, place_name, window_in_days = 30):
    yelp_ratings = load_data('ratings/%s' % place_name)
    ratings_before = []
    ratings_after = []
    for r in yelp_ratings:
        rating_date = dateutil.parser.parse(r[1])
        #print '%s: %s (%s)' % (r[0], rating_date, r[1])
        diff = (rating_date - date).days
        if (abs(diff) <= window_in_days):
            if diff > 0:
                ratings_after.append(int(r[0]))
            else:
                ratings_before.append(int(r[0]))
    return {'before': {'count': len(ratings_before), 'avg': numpy.average(ratings_before)},
            'after': {'count': len(ratings_after), 'avg': numpy.average(ratings_after)}} 
    

def get_manhattan_nyc_inspection_ratings():
    loader = NycInspectionLoader()
    loader.load()
    # manhattan is region 1
    loader.filter_by_region(1)
    data = loader.get_data()
    ratings = {}
    data['WebExtract'].sort(order='inspdate')
    for violation in data['WebExtract']:
        rating = violation['currentgrade']
        if rating not in ['A', 'B', 'C']:
            continue
        biz_id = violation['camis']
        if biz_id not in ratings:
            ratings[biz_id] = []
        date = violation['inspdate']
        last_date = None if len(ratings[biz_id]) == 0 else ratings[biz_id][-1]['inspdate']
        if last_date != date:
            #print '%s, %s : %s' % (violation['dba'], last_date, date)
            ratings[biz_id].append(violation)

    print "Num unique restaurants in Manhattan: %d" % (len(ratings))
    return ratings

def find_closest_yelp_business(query_biz):
    matches = get_search_results(query_biz['dba'], query_biz['zipcode'])
    if (len(matches) > 0):
        print '%s: %s' % (query_biz['dba'], matches[0])
        return matches[0]    
    print 'Warning: no match found for business "%%s"' % query_biz['dba']
    return None


def correlate_restaurants():
    restaurants = keys(get_manhattan_nyc_inspection_ratings())
    correlated_restaurants = []
    for r in restaurants:
        try:
            b = find_closest_yelp_business(r)
            correlated_restaurants.append([b, r])
        except:
            print "Unable to find yelp biz for %s" % (r['dba'])
    return correlated_restaurants
    
def print_correlated_restaurants(correlated_restaurants, places):
    pass

mode = sys.argv[1]
if mode == 'get-top':
    places = get_top_places()
    write_data('top_places', places)
elif mode == 'print-top':
    places = load_data('top_places')
    print_top_places(places)
elif mode == 'crawl-top-places':    
    places = load_data('top_places')
    crawl_all_places(places)
elif mode == 'crawl-place':
    place_name = sys.argv[2]
    crawl_place(place_name)
elif mode == 'print-place':
    place = sys.argv[2]
    ratings = load_data('ratings/%s' % place)
    print ratings
elif mode == 'find-yelp-biz':
    name = sys.argv[2]
    zipcode = sys.argv[3]
    print find_closest_yelp_business({'dba': name, 'zipcode': zipcode})
elif mode == 'correlate-restaurants':
    cr = correlate_restaurants()
    write_data('correlated_restaurants', cr)
elif mode == 'print-correlated-restaurants':
    cr = load_data('correlated_restaurants')
    places = None
    if sys.argv[2] == 'top':
        places = load_data('top_places')
    print_correlated_restaurants(cr, places)
elif mode == 'ratings-around-date':
    date = dateutil.parser.parse(sys.argv[2])
    place_name = sys.argv[3]
    window = int(sys.argv[4])
    print ratings_around_date(date, place_name, window)
elif mode == 'get-ratings':
    ratings = get_manhattan_nyc_inspection_ratings()
    biz = sys.argv[2]
    for r_seq in ratings.itervalues():
        if r_seq[0]['dba'] == biz:
            print 'Business: %s' % biz
            for r in r_seq:
                print '\t%s: %s' % (r['inspdate'], r['currentgrade'])
