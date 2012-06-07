import sys
import re

class BiznameComparer:
        
    def canonicalize_name(self, name, is_yelp = False):
        name = name.lower()
        name = name.replace('-', ' ')
        if is_yelp:
            m = re.search('([^/]+)$', name)
            name = m.group(0)
            name = re.sub('new york\s{0,1}\d*$', '', name)
            name = re.sub('manhattan\s{0,1}\d*$', '', name)
            name = name.strip()
        name = name.replace('\'', '')        
        return name
            
    def filter_stopwords(self, words):
        stop_words = ['&', 'and']
        return filter(lambda w: w not in stop_words, words)

    def compare(self, name, yelp_url):
        name = self.canonicalize_name(name, False)
        yelp_name = self.canonicalize_name(yelp_url, True)
        split_and_process = lambda s: set(self.filter_stopwords(s.split()))
        w1 = split_and_process(name)
        w2 = split_and_process(yelp_name)
        return len(w1.intersection(w2)) / float(len(w1.union(w2)))
        
        
    
