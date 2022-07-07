#!/usr/bin/env python
import os, sys, re, logging, json, requests, shutil
from pprint import pprint

from measures import app
from measures.lib.airs_modis import convert, get_metadata
from measures.lib.plot import plot_airs_modis_matchup, create_browse_small


logging.basicConfig(level=logging.DEBUG)


H4_RE = re.compile(r'COL_NEAREST_V5_MODIS_AIRS_(\d{4})(\d{2})(\d{2})_(\d{4}).hdf$')


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

    search_url = '%s/%s/_search' % (app.config['ES_URL'], app.config['AIRS_MODIS_INDEX'])
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
    # HDF4 file
    h4_file = sys.argv[1]

    # extract date/time
    match = H4_RE.search(h4_file)
    if not match:
        raise RuntimeError("Failed to extract date/time from %s." % h4_file)
    yy, mm, dd, tt = match.groups()

    # get product ID
    product_id = "index-airs.aqua_modis.aqua-v%s-%s.%s.%s.%s" % (
        app.config['AIRS_MODIS_VERSION'], yy, mm, dd, tt)

    # check if already exists
    if product_exists(product_id):
        print ("Product %s already exists." % product_id)
        sys.exit(0)

    # get product directory
    product_dir = product_id
    if not os.path.isdir(product_dir):
        os.makedirs(product_dir)

    # convert
    nc4_file = os.path.join(product_dir, "%s.nc4" % product_id)
    try: convert(h4_file, nc4_file)
    except Exception, e:
        if os.path.exists(product_dir):
            shutil.rmtree(product_dir)
        raise
    
    # create plot files
    plot_file = os.path.join(product_dir, "%s.browse.png" % product_id)
    plot_airs_modis_matchup(nc4_file, plot_file, map_global=True)
    plot_file_small = os.path.join(product_dir, "%s.browse_small.png" % product_id)
    create_browse_small(plot_file, plot_file_small)

    ## write metadata file
    metadata_file = os.path.join(product_dir, "%s.met.json" % product_id)
    with open(metadata_file, 'w') as f:
        json.dump(get_metadata(nc4_file, ''), f, indent=2)


if __name__ == "__main__":
    main()
