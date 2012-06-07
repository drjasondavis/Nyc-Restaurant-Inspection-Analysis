#!/bin/bash

mkdir data
echo "Fetching restaurant data to data/ratings.zip"
wget https://nycopendata.socrata.com/download/4vkw-7nck/ZIP -O data/ratings.zip

echo "Unzipping ratings"
unzip data/ratings.zip

echo "Deleting ratings"
rm -f data/ratings.zip

mkdir pickle
mkdir pickle/ratings