#!/usr/bin/env python
import os, sys, logging, json
from pprint import pprint

from measures import app
from measures.lib.query import search


logging.basicConfig(level=logging.DEBUG)


def test_query_matchup_indices():
    """Test querying matchup indices."""

    dataset = 'WVCC_MATCHUP_INDICES'
    level = 'L2'
    version = 'v4.0'
    starttime = '2006-07-24T00:00:00Z'
    endtime = '2006-07-24T12:59:59Z'
    lat_min = -24
    lat_max = 0
    lon_min = -34
    lon_max = 0
    response_group = 'Medium'
    res = search(dataset, level, version, starttime, endtime, lat_min,
                 lat_max, lon_min, lon_max, response_group)
    print(res)
    print json.loads(res)['count']
           
    
if __name__ == "__main__":
    test_query_matchup_indices()
