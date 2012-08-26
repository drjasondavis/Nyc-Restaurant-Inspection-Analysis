import sys
import matplotlib.mlab as mlab
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import operator
import numpy


PLOT_DIR = "plot"

class RestaurantGradeChanges:
    
    def __init__(self, data):
        self.data = data

    def extract_restaurant_ratings(self):
        self.ratings = {'inspection': {}, 'yelp': {}}
        self.restaurant_yelp_ratings = {}
        self.yelp_rating_counts_by_day = {}
        for d in self.data:
            restaurant_name = d['yelp_biz_name']
            rating_type = d['rating_type']
            rating = d['rating']
            rating_date = d['rating_date']
            rating_dictionary = None
            if rating_type == 'yelp':
                if rating_date not in self.yelp_rating_counts_by_day:
                    self.yelp_rating_counts_by_day[rating_date] = 0
                self.yelp_rating_counts_by_day[rating_date] += 1
            if restaurant_name not in self.ratings[rating_type]:
                self.ratings[rating_type][restaurant_name] = []
            self.ratings[rating_type][restaurant_name].append(d)
        self.yelp_rating_counts_by_day = sorted(self.yelp_rating_counts_by_day.iteritems(), key=operator.itemgetter(0))
        counts = map(operator.itemgetter(1), self.yelp_rating_counts_by_day)
        window = 3
        smoothed_counts = numpy.convolve(numpy.ones(window, 'd')/window, counts, mode='same')
        self.yelp_rating_counts_by_day = dict(zip(map(operator.itemgetter(0), self.yelp_rating_counts_by_day), smoothed_counts))

    def get_rating_counts_over_time(self, rating_type):
        return self._aggregate_over_time(rating_type, lambda x: len(x))
    
    def get_yelp_rating_changes(self,  window_in_days = 60):
        rating_dates = {}
        for restaurant, ratings in self.ratings['inspection'].iteritems():
            last_inspection_rating = 'None'
            for r in ratings:
                inspection_rating = r['rating']
                inspection_rating_date = r['rating_date']
                key = '%s -> %s' % (last_inspection_rating, inspection_rating)
                if key not in rating_dates:
                    rating_dates[key] = {}
                yelp_rating_change_count_before_window = 0
                yelp_rating_change_count_after_window = 0
                for yelp_rating in self.ratings['yelp'][restaurant]:
                    yelp_rating_date = yelp_rating['rating_date']
                    time_delta = (yelp_rating_date - inspection_rating_date).days
                    if (abs(time_delta) < window_in_days):
                        if time_delta < 0:
                            yelp_rating_change_count_before_window += 1
                        else: 
                            yelp_rating_change_count_after_window += 1
                        if time_delta not in rating_dates[key]:
                            rating_dates[key][time_delta] = []
                        normalized_count = 1.0 / self.yelp_rating_counts_by_day[yelp_rating_date]
                        rating_dates[key][time_delta].append({'rating': yelp_rating['rating'], 'yelp_biz_name': restaurant, 'normalized_count': normalized_count, 'count': 1})
                print '%s, %s, count: (%d, %d), date: %s' % (restaurant, key, yelp_rating_change_count_before_window, yelp_rating_change_count_after_window, inspection_rating_date)
                last_inspection_rating = inspection_rating
        return rating_dates

    def get_avg_ratings_over_time(self, rating_type):
        fn = None
        if rating_type == 'yelp':
            fn = lambda grade_ratings: numpy.average(map(lambda x: float(x), grade_ratings))
        elif rating_type == 'inspection':
            fn = lambda grade_ratings: numpy.average(map(lambda x: 5 + ord('A') - ord(x), grade_ratings))
        return self._aggregate_over_time(rating_type, fn)

    def _aggregate_over_time(self, rating_type, aggregation_function):
        grouped_by_date = {}
        for d in self.data:
            rt = d['rating_type']
            date = d['rating_date']
            if rt != rating_type:
                continue
            if date not in grouped_by_date:
                grouped_by_date[date] = []
            grouped_by_date[date].append(d['rating'])
        aggregated = {}
        for date, ratings in grouped_by_date.iteritems():
            aggregated[date] = aggregation_function(ratings)
        return sorted(aggregated.iteritems(), key=operator.itemgetter(0))
        
            
class Plot:
    
    def __init__(self, name, xlabel, ylabel, title = None):
        self.name = name
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.title = title
    
    def plot_time(self, time_value_dict):
        time_value_dict = sorted(time_value_dict, key=operator.itemgetter(0))
        f = plt.figure() 
        x = []
        y = []
        for [t, r] in time_value_dict:
            x.append(t)
            y.append(r)
            
        smoothing_window = 10
        y = numpy.convolve(numpy.ones(smoothing_window, 'd')/smoothing_window, y, mode='valid')
        plt.plot(x[0:len(y)], y)
        plt.xlabel(self.xlabel)
        plt.ylabel(self.ylabel)
        f.autofmt_xdate()
        if self.title != None:
            plt.title(self.title)
        plt.savefig(PLOT_DIR + "/" + self.name + ".png")

filename = sys.argv[1]
data = mlab.csv2rec(filename)

grade_changes = RestaurantGradeChanges(data)
grade_changes.extract_restaurant_ratings()

for rating_type in ['yelp', 'inspection']:
    title = '%s ratings over time' % (rating_type)
    Plot(rating_type + "_ratings_count_over_time", "", "ratings per day", title).plot_time(grade_changes.get_rating_counts_over_time(rating_type))
    Plot(rating_type + "_ratings_avg_over_time", "", "average rating").plot_time(grade_changes.get_avg_ratings_over_time(rating_type))

rating_changes = grade_changes.get_yelp_rating_changes()
for rating_change, day_values in rating_changes.iteritems():
    time_counts = {}
    time_ncounts = {}
    time_averages = {}
    for d, array in day_values.iteritems():
        time_counts[d] = len(array)
        time_ncounts[d] = sum(map(lambda x: float(x['normalized_count']), array))
        time_averages[d] = numpy.average(map(lambda x: float(x['rating']), array))
    
    positive_filter = lambda y: map(lambda z: z[1], filter(lambda x: x[0] >= 0, y.iteritems()))
    negative_filter = lambda y: map(lambda z: z[1], filter(lambda x: x[0] < 0, y.iteritems()))
    before_count = sum(negative_filter(time_counts))
    after_count = sum(positive_filter(time_counts))
    diff_count = (after_count / float(before_count)) - 1.0

    before_ncount = sum(negative_filter(time_ncounts))
    after_ncount = sum(positive_filter(time_ncounts))
    diff_ncount = (after_ncount / float(before_ncount)) - 1.0

    before_avg = numpy.average(negative_filter(time_averages))
    after_avg = numpy.average(positive_filter(time_averages))
    diff_avg = (after_avg / float(before_avg)) - 1.0
    print '%15s: Count before:            %4d,   after: %4d, Diff: %.3f' % (rating_change, before_count, after_count, diff_count)
    print '%15s: Normalized Count before: %2.2f, after: %2.2f, Diff: %.3f' % (rating_change, before_ncount, after_ncount, diff_ncount)
    print '%15s: Avg before:              %1.2f, after: %1.2f, Diff: %.3f' % (rating_change, before_avg, after_avg, diff_avg)
    print "\n"
    Plot(rating_change + "_count", "time", "count").plot_time(time_counts.iteritems())
    Plot(rating_change + "_average", "time", "average rating").plot_time(time_averages.iteritems())
