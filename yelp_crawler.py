import os
import sys
import re
import csv

import json

import dateutil.parser
import urllib
import urllib2
import pickle
import time
import numpy
import matplotlib.mlab as mlab

from nyc_inspection_loader import NycInspectionLoader
import bizname_comparer
from helper import *

REGION = 'Manhattan'
QUERY = 'Restaurants'
NUM_TOP_PLACES = 1000
CRAWL_TIMEOUT_SECONDS = 0
PICKLE_DIR = 'pickle'
USER_AGENT = 'nyc-restaurant-inspector'

reg = re.compile('<span class="value-title" title="(\d)"></span>\s+</div>\s+<em class="dtreviewed smaller">(\d+/\d+/\d+) <span', re.MULTILINE)
search_reg = re.compile('<a id="bizTitleLink\d+" href="([^"?#]+)[^"]*">\d+\.')


def write_data(name, data):
    pickle.dump(data, open(pkl_filename(name), 'wb'))

def load_data(name):
    return pickle.load(open(pkl_filename(name), 'rb'))

def get_search_results(desc, loc, start = 0):
    time.sleep(CRAWL_TIMEOUT_SECONDS)
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

def ratings_around_date(date, place_name, window_in_days = 90):
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
    return [ratings_before, ratings_after]
    

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
    return ratings

def find_closest_yelp_business(query_biz):
    matches = get_search_results(query_biz['dba'], query_biz['zipcode'])
    if (len(matches) > 0):
        print '%s: %s' % (query_biz['dba'], matches[0])
        return matches[0]    
    print 'Warning: no match found for business "%%s"' % query_biz['dba']
    return None


def correlate_restaurants(correlated_restaurants = []):
    correlated_ids = {}
    for x in correlated_restaurants:
        correlated_ids[x[1]] = True
    print "Num existing correlations: %d" % len(correlated_ids)
    restaurants = get_manhattan_nyc_inspection_ratings()
    for biz_id, ratings in restaurants.iteritems():
        r = ratings[0]
        if biz_id in correlated_ids:
            print "Yelp biz already correlated: %s" % r['dba']
            continue
        b = ""
        try:
            b = find_closest_yelp_business(r)
        except urllib2.URLError, e:
            print "Url error: %s" % e
            if e.code == 500: 
                continue
            return correlated_restaurants
        except:
            print "Unable to find yelp biz for %s" % (r['dba'])
        correlated_restaurants.append([b, biz_id])
    return correlated_restaurants

def correlate_top_restaurant_inspections():
    yelp_nyc_id_map = load_data('correlated_restaurants')
    ratings = get_manhattan_nyc_inspection_ratings()
    places = load_data('top_places')
    comparer = bizname_comparer.BiznameComparer()
    yelp_nyc_businesses = {}
    for x in yelp_nyc_id_map:
        yelp_biz_name = x[0]
        if yelp_biz_name == '':
            continue
        biz_id = x[1]
        if yelp_biz_name not in yelp_nyc_businesses:
            yelp_nyc_businesses[yelp_biz_name] = []
        yelp_nyc_businesses[yelp_biz_name].append(biz_id)
    yelp_biz_ids = {}
    for yelp_biz_name, biz_ids in yelp_nyc_businesses.iteritems():        
        best_score = -1
        best_bid = -1
        for bid in biz_ids:
            biz_name = ratings[bid][0]['dba']            
            score = comparer.compare(biz_name, yelp_biz_name)
            if score > best_score:
                best_bid, best_score = bid, score
        yelp_biz_ids[yelp_biz_name] = best_bid
    ratings_before = {}
    ratings_after = {}
    rating_switches = 0
    uniq_biz_ids = {}
    def date_format(d):
        return d.strftime("%m/%d/%y")
    csv.writer(sys.stdout).writerow(['yelp_biz_name', 'rating_type', 'rating_date', 'rating'])
    for yelp_biz_name, biz_id in yelp_biz_ids.iteritems():
        if biz_id in uniq_biz_ids:
            continue
        uniq_biz_ids[biz_id] = True
        yelp_biz_name = yelp_biz_name.replace('/biz/', '')
        if yelp_biz_name not in places:
            continue

        try: 
            yelp_biz_ratings = load_data('ratings/%s' % yelp_biz_name)
            for r in yelp_biz_ratings:
                rating = r[0]
                rating_date = dateutil.parser.parse(r[1])
                csv.writer(sys.stdout).writerow([yelp_biz_name, 'yelp', date_format(rating_date), rating])
                
            biz_ratings = ratings[biz_id]
            for r in biz_ratings:
                csv.writer(sys.stdout).writerow([yelp_biz_name, 'inspection', date_format(r['inspdate']), r['currentgrade']])
        except:
            e = sys.exc_info()[1]
            sys.stderr.write("Error processing ratings for %s: %s\n" % (yelp_biz_name, e))
            
       


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
    existing_cr = load_data('correlated_restaurants')
    cr = correlate_restaurants(existing_cr)
    write_data('correlated_restaurants', cr)
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
elif mode == 'correlate-top-restaurant-inspections':
    correlate_top_restaurant_inspections()
