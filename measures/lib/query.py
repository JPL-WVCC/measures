import os, sys, time, json, requests
from pprint import pformat
from datetime import datetime, timedelta
from shapely.geometry import box

from measures import app


def search(dataset, level, version, starttime, endtime, lat_min,lat_max,
           lon_min, lon_max, response_group):
    """Geospatial and temporal query of WVCC matchup indices."""

    # get ES index and url
    if dataset == 'WVCC_MATCHUP_INDICES':
        es_index = app.config['ES_INDEX']
    elif dataset == 'WVCC_MERGED_DATA':
        es_index = app.config['ES_MERGED_DATA_INDEX']
    else:
        raise RuntimeError("Unrecognized dataset: %s" % dataset)
    es_url = app.config['ES_URL']
    #app.logger.debug(app.config['GRQ_URL'])

    # date range filter
    if starttime is None and endtime is None:
        date_filter = None
    elif starttime is not None and endtime is not None:
        starttime = starttime.replace(' ', 'T')
        endtime = endtime.replace(' ', 'T')
        date_filter = {
            "bool": {
                "must": [
                    {
                        "range": {
                            "starttime": {
                                "lte": endtime
                            }
                        }
                    },
                    {
                        "range": {
                            "endtime": {
                                "gte": starttime
                            }
                        }
                    }
                ]
            }
        }
    else:
        raise RuntimeError("Invalid starttime and endtime: %s %s" % (starttime, enddtime))

    # location filter
    if lat_min == -90. and lat_max == 90. and lon_min == -180. and lon_max == 180.:
        loc_filter = None
        loc_filter_box = None
    else:
        loc_filter = {
            "geo_shape" : {
                "location" : {
                    "shape": {
                        "type": "envelope",
                        "coordinates": [
                            [ lon_min, lat_max ],
                            [ lon_max, lat_min ]
                        ]
                    }
                }
            }
        }
        loc_filter_box = box(*map(float, [lon_min, lat_min, lon_max, lat_max]))

    # build query
    query = {
        "sort": {
            "_id": {
                "order": "desc"
            }
        },
        "fields": [
            "_timestamp",
            "_source"
        ],
        "query": {
            "term": { "dataset": dataset }
        }
    }

    # add filters or query_string queries
    qs_queries = []
    filters = []
    if date_filter is not None: filters.append(date_filter)
    if loc_filter is not None: filters.append(loc_filter)
    if len(filters) > 0: query['filter'] = { "and": filters }
    if len(qs_queries) > 0: query['query'] = { "bool": { "must": qs_queries } }

    # query for results
    #app.logger.debug("ES query for grq(): %s" % json.dumps(query, indent=2))
    r = requests.post('%s/%s/_search?search_type=scan&scroll=10m&size=100' %
                      (es_url, es_index), data=json.dumps(query))
    if r.status_code != 200:
        print(r.json())
    r.raise_for_status()
    scan_result = r.json()
    count = scan_result['hits']['total']
    scroll_id = scan_result['_scroll_id']
    results = []
    while True:
        r = requests.post('%s/_search/scroll?scroll=10m' % es_url, data=scroll_id)
        res = r.json()
        scroll_id = res['_scroll_id']
        if len(res['hits']['hits']) == 0: break
        results.extend(res['hits']['hits'])

    # return json
    return json.dumps({'results': results, 'count': len(results)}, indent=2)
