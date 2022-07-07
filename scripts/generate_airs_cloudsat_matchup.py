#!/usr/bin/env python
import os, sys, logging, json, requests, shutil
from pprint import pprint
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
import pydap.lib
from pydap.client import open_url
import cPickle as pickle

from measures import app
from measures.lib import airs as measures_airs
from measures.lib import cloudsat as measures_cs
from measures.lib.utils import filter_info
from measures.lib.plot import plot_airs_cloudsat_matchup, create_browse_small


#pydap.lib.CACHE = "/data/work/tmp/pydap_cache/"
pydap.lib.TIMEOUT = 60

logging.basicConfig(level=logging.DEBUG)

# time tolerance in seconds
time_tol = 300.

# distance tolerance in km
dist_tol = 12.

dap_filter = "^http://cvo.hysds.net:8080/opendap/.*\.hdf$"
url_prop = "urls"
dap_prop = "dap_urls"


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

    search_url = '%s/%s/_search' % (app.config['ES_URL'], app.config['ES_INDEX'])
    r = requests.post(search_url, data=json.dumps(query))
    if r.status_code != 200:
        print >>sys.stderr, "Failed to query %s:\n%s" % (search_url, r.text)
        print >>sys.stderr, "query: %s" % json.dumps(query, indent=2)
        print >>sys.stderr, "returned: %s" % r.text
    r.raise_for_status()
    result = r.json()
    #pprint(result)
    total = result['hits']['total']
    return total > 0


def main():
    # AIRS DAP url
    airs_dap_url = sys.argv[1]

    # get product ID
    product_id = "index-airs.aqua_cloudsat-v%s-%s" % (app.config['MATCHUP_VERSION'],
                                                      os.path.basename(airs_dap_url)[5:19])

    # check if already exists
    if product_exists(product_id):
        print "Product %s already exists." % product_id
        sys.exit(0)

    # get product directory
    product_dir = product_id
    if not os.path.isdir(product_dir):
        os.makedirs(product_dir)

    # get AIRS time info
    a_tinfo = measures_airs.get_time_info(airs_dap_url)
    
    # get matching CloudSat granules
    cs_minfo = measures_airs.grq_cloudsat(a_tinfo['start_utc'], a_tinfo['end_utc'])
    
    # filter dap urls
    filter_info(cs_minfo, dap_filter, url_prop, dap_prop)
    
    # get cloudsat granule time array
    cs_tinfo = measures_cs.get_granule_times(cs_minfo)
    
    # coarse matchup
    matched_cs_ids = measures_airs.coarse_match_cloudsat(a_tinfo, cs_tinfo, time_tol)
    
    # fine matchup
    matchup_file = os.path.join(product_dir, "%s.nc4" % product_id)
    try:
        measures_airs.fine_match_cloudsat(airs_dap_url, a_tinfo, matched_cs_ids,
                                          cs_tinfo, cs_minfo, matchup_file, 
                                          dist_tol, time_tol)
    except Exception, e:
        if os.path.exists(product_dir):
            shutil.rmtree(product_dir)
        raise
    
    # create matchup text file
    matchup_txt_file = os.path.join(product_dir, "%s.txt" % product_id)
    measures_airs.write_matchup_txt(matchup_file, matchup_txt_file)

    # create plot files
    plot_file = os.path.join(product_dir, "%s.browse.png" % product_id)
    plot_airs_cloudsat_matchup(matchup_file, plot_file)
    plot_file_small = os.path.join(product_dir, "%s.browse_small.png" % product_id)
    create_browse_small(plot_file, plot_file_small)
    global_plot_file = os.path.join(product_dir, "%s.global.browse.png" % product_id)
    plot_airs_cloudsat_matchup(matchup_file, global_plot_file, map_global=True)
    global_plot_file_small = os.path.join(product_dir, "%s.global.browse_small.png" % product_id)
    create_browse_small(global_plot_file, global_plot_file_small)

    # write metadata file
    metadata_file = os.path.join(product_dir, "%s.met.json" % product_id)
    with open(metadata_file, 'w') as f:
        json.dump(measures_airs.get_metadata(matchup_file, ''), f, indent=2)


if __name__ == "__main__":
    main()
