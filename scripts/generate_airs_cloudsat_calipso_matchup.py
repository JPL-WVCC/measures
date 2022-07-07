#!/usr/bin/env python
import os, sys, logging, json, requests, shutil, re, time
from netCDF4 import Dataset
from pprint import pprint
import pydap.lib
from pydap.client import open_url
from datetime import datetime, timedelta
import cPickle as pickle

from measures import app
from measures.lib.calipso import (get_dap_urls, get_granule_times,
coarse_match_cloudsat, fine_match_cloudsat)
from measures.lib.airs import get_metadata
from measures.lib.plot import plot_airs_cloudsat_calipso_matchup, create_browse_small


# AIRS-CloudSat matchup file regex
AIRS_CS_RE = re.compile(r'index-airs\.aqua_cloudsat-(v\d\.\d)-(\d{4}\.\d{2}\.\d{2}\.\d{3})\.nc4$')

#pydap.lib.CACHE = "/data/work/tmp/pydap_cache/"
pydap.lib.TIMEOUT = 60

logging.basicConfig(level=logging.DEBUG)

# time tolerance in seconds
time_tol = 300.

# distance tolerance in km
dist_tol = 12.


def product_exists(product_id):
    """Query for products with specified ID."""

    query = {
        "query":{
            "bool":{
                "must":[
                    {"term":{"id": product_id}},
                ]
            }
        }
    }
    #print json.dumps(query, indent=2)

    search_url = '%s/%s/_search' % (app.config['ES_URL'], app.config['ACC_ES_INDEX'])
    r = requests.post(search_url, data=json.dumps(query))
    result = r.json()
    #pprint(result)
    if r.status_code == 404 and result.get('error', '').startswith('IndexMissingException'):
        return False
    if r.status_code != 200:
        print >>sys.stderr, "Failed to query %s:\n%s" % (search_url, r.text)
        print >>sys.stderr, "query: %s" % json.dumps(query, indent=2)
        print >>sys.stderr, "returned: %s" % r.text
        r.raise_for_status()
    total = result['hits']['total']
    return total > 0


def main():
    airs_cloudsat_file = sys.argv[1]
    calipso_dap_url_base = sys.argv[2]

    # get product ID
    match = AIRS_CS_RE.search(os.path.basename(airs_cloudsat_file))
    if not match:
        raise(RuntimeError("Failed to match AIRS-CloudSat matchup filename."))
    product_id = "index-airs.aqua_cloudsat_caliop.calipso-%s-%s" % match.groups()

    # check if already exists
    if product_exists(product_id):
        print "Product %s already exists." % product_id
        sys.exit(0)

    # get product directory and matchup file
    product_dir = product_id
    if not os.path.isdir(product_dir):
        os.makedirs(product_dir)
    matchup_file = os.path.join(product_dir, '%s.nc4' % product_id)

    # copy matchup file
    shutil.copy(airs_cloudsat_file, matchup_file)

    # open matchup file
    rootgrp = Dataset(matchup_file, 'a')
    
    # get CloudSat time and dap_url variables
    time_cs = rootgrp.variables['time_cs']
    cs_dap_urls = rootgrp.variables['cloudsat_dap_url']

    # create CloudSat time info
    cs_tinfo = { 'profile_utc': time_cs[:],
                 'start_utc': time_cs[0],
                 'end_utc': time_cs[-1] }

    # get starting and ending cloudsat times
    elts = time.gmtime(cs_tinfo['start_utc'])
    time_cs_i = datetime(*elts[0:3]) - timedelta(days=1)
    elts = time.gmtime(cs_tinfo['end_utc'])
    time_cs_f = datetime(*elts[0:3]) + timedelta(days=1)
    #print time_cs_i, time_cs_f

    # get list of CALIPSO dap urls using thredds catalog
    cal_dap_urls = get_dap_urls(calipso_dap_url_base, time_cs_i, time_cs_f)

    # get calipso granule time array
    #pickle_file = 'cal_tinfo.pkl'
    #if os.path.exists(pickle_file):
    #    with open(pickle_file) as f:
    #        cal_tinfo = pickle.load(f)
    #else:
    #    cal_tinfo = get_granule_times(cal_dap_urls)
    #    with open(pickle_file, 'w') as f:
    #        pickle.dump(cal_tinfo, f)
    cal_tinfo = get_granule_times(cal_dap_urls)
    #pprint(cal_tinfo)

    # coarse matchup
    matched_cal_urls = coarse_match_cloudsat(cs_tinfo, cal_tinfo, time_tol)

    # fine matchup
    try:
        fine_match_cloudsat(airs_cloudsat_file, matchup_file, rootgrp,
                            cs_tinfo, matched_cal_urls, cal_tinfo, 
                            dist_tol, time_tol)
    except Exception, e:
        if os.path.exists(product_dir):
            shutil.rmtree(product_dir)
        raise

    # close nc4 file
    rootgrp.close()

    # create plot files
    plot_file = os.path.join(product_dir, "%s.browse.png" % product_id)
    plot_airs_cloudsat_calipso_matchup(matchup_file, plot_file)
    plot_file_small = os.path.join(product_dir, "%s.browse_small.png" % product_id)
    create_browse_small(plot_file, plot_file_small)
    global_plot_file = os.path.join(product_dir, "%s.global.browse.png" % product_id)
    plot_airs_cloudsat_calipso_matchup(matchup_file, global_plot_file, map_global=True)
    global_plot_file_small = os.path.join(product_dir, "%s.global.browse_small.png" % product_id)
    create_browse_small(global_plot_file, global_plot_file_small)

    # write metadata file
    metadata_file = os.path.join(product_dir, "%s.met.json" % product_id)
    with open(metadata_file, 'w') as f:
        json.dump(get_metadata(matchup_file, '', 'AIRS_CLOUDSAT_CALIPSO_MATCHUP_INDICES'), f, indent=2)


if __name__ == "__main__":
    main()
