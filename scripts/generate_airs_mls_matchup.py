#!/usr/bin/env python
import os, sys, re, logging, json, requests, shutil, argparse
from pprint import pprint

from measures import app
from measures.lib.airs_mls import convert, get_metadata
from measures.lib.plot import plot_airs_mls_matchup, create_browse_small


logging.basicConfig(level=logging.DEBUG)


MAT_RE = re.compile(r'AIRS_MLS_MATCHUP_(\d{4})_(\d{2})_(\d{2}).mat$')


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

    search_url = '%s/%s/_search' % (app.config['ES_URL'], app.config['AIRS_MLS_INDEX'])
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


def main(mat_file, joined_file):

    # extract date/time
    match = MAT_RE.search(mat_file)
    if not match:
        raise RuntimeError("Failed to extract date/time from %s." % mat_file)
    yy, mm, dd = match.groups()

    # get product ID
    product_id = "index-airs.aqua_mls.aura-v%s-%s.%s.%s" % (
        app.config['AIRS_MLS_VERSION'], yy, mm, dd)

    # check if already exists
    if product_exists(product_id):
        print "Product %s already exists." % product_id
        sys.exit(0)

    # get product directory
    product_dir = product_id
    if not os.path.isdir(product_dir):
        os.makedirs(product_dir)

    # convert
    nc_file = os.path.join(product_dir, "%s.nc" % product_id)
    try: convert(mat_file, joined_file, nc_file)
    except Exception, e:
        if os.path.exists(product_dir):
            shutil.rmtree(product_dir)
        raise
    
    # create plot files
    plot_file = os.path.join(product_dir, "%s.browse.png" % product_id)
    plot_airs_mls_matchup(nc_file, plot_file)
    plot_file_small = os.path.join(product_dir, "%s.browse_small.png" % product_id)
    create_browse_small(plot_file, plot_file_small)

    # write dataset and metadata file
    ds_info = get_metadata(nc_file, '')
    met_file = os.path.join(product_dir, "%s.met.json" % product_id)
    ds_file = os.path.join(product_dir, "%s.dataset.json" % product_id)
    with open(met_file, 'w') as f:
        json.dump(ds_info['metadata'], f, indent=2, sort_keys=True)
    with open(ds_file, 'w') as f:
        json.dump(ds_info['dataset'], f, indent=2, sort_keys=True)


if __name__ == "__main__":
   desc = "Convert AIRS-MLS matchup and joined MAT-files to NetCDF4 and add metadata and browse image."
   parser = argparse.ArgumentParser(description=desc)
   parser.add_argument('mat_file', help="input matchup MAT-file")
   parser.add_argument('joined_file', help="input joined MAT-file")
   args = parser.parse_args()
   main(args.mat_file, args.joined_file)
