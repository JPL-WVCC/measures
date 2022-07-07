#!/usr/bin/env python
import os, sys, logging, json, requests, shutil, re, traceback
from pprint import pprint

from measures import app
from measures.lib.merge_data import merge_airs_cloudsat
from measures.lib.plot import plot_airs_cloudsat_matchup, plot_cloud_scene, create_browse_small
from measures.lib.varlist import create_cfg
from measures.lib import airs as measures_airs


#logging.basicConfig(format="[%(asctime)s: %(levelname)s/%(name)s] %(message)s", level=logging.WARNING)
#logging.getLogger('pydap').setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)


GRANULE_RE = re.compile(r'-(\d{4}\.\d{2}\.\d{2}\.\d{3})\.nc4')


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

    search_url = '%s/%s/_search' % (app.config['ES_URL'], app.config['ES_MERGED_DATA_INDEX'])
    r = requests.post(search_url, data=json.dumps(query))
    if r.status_code != 200:
        logging.error("Failed to query %s:\n%s" % (search_url, r.text))
        logging.error("query: %s" % json.dumps(query, indent=2))
        logging.error("returned: %s" % r.text)
    r.raise_for_status()
    result = r.json()
    #pprint(result)
    total = result['hits']['total']
    return total > 0


def main():
    matchup_file = sys.argv[1] # AIRS-CloudSat matchup file
    varlist_json_file = sys.argv[2] # variable list configuration

    # get product ID
    match = GRANULE_RE.search(os.path.basename(matchup_file))
    if not match:
        raise RuntimeError("Couldn't extract granule info from file name: %s" % matchup_file)
    product_id = "matched-airs.aqua_cloudsat-v%s-%s" % (app.config['MERGED_DATA_VERSION'],
                                                       match.group(1))

    # check if already exists
    if product_exists(product_id):
        logging.error("Product %s already exists." % product_id)
        sys.exit(0)

    # get product directory
    product_dir = product_id
    if not os.path.isdir(product_dir):
        os.makedirs(product_dir)

    # if context.json exists create varlist_config from params
    if os.path.exists('context.json'):
        with open('context.json') as f: ctx = json.load(f)
        total_vars = 0
        for k in ('cs_geoprof_vars', 'cs_cldclass_vars', 'cs_geoprof_lidar_vars',
                  'airs_retstd_vars', 'airs_retsup_vars', 'airs_rad_vars'):
            total_vars += len(ctx[k])
        if total_vars > 0:
            varlist_json_file = create_cfg(ctx['cs_geoprof_vars'],
                                           ctx['cs_cldclass_vars'],
                                           ctx['cs_geoprof_lidar_vars'],
                                           ctx['airs_retstd_vars'],
                                           ctx['airs_retsup_vars'],
                                           ctx['airs_rad_vars'],
                                           'filtered_varlist_config.json')

    # generate merged data
    merged_file = os.path.join(product_dir, "%s.nc4" % product_id)
    try:
        merge_airs_cloudsat(matchup_file, varlist_json_file, merged_file)
        # hit DAP at Goddard
        #merge_airs_cloudsat(matchup_file, varlist_json_file, merged_file,
        #                    airs_url_match="ecs\.nasa\.gov/opendap")
    except Exception, e:
        with open('_alt_error.txt', 'w') as f:
            f.write("%s\n" % str(e))
        with open('_alt_traceback.txt', 'w') as f:
            f.write("%s\n" % traceback.format_exc())
        if os.path.exists(product_dir):
            shutil.rmtree(product_dir)
        raise
    
    # create matchup location plot files
    try:
        plot_file = os.path.join(product_dir, "%s.browse.png" % product_id)
        plot_airs_cloudsat_matchup(merged_file, plot_file)
        plot_file_small = os.path.join(product_dir, "%s.browse_small.png" % product_id)
        create_browse_small(plot_file, plot_file_small)
        global_plot_file = os.path.join(product_dir, "%s.global.browse.png" % product_id)
        plot_airs_cloudsat_matchup(merged_file, global_plot_file, map_global=True)
        global_plot_file_small = os.path.join(product_dir, "%s.global.browse_small.png" % product_id)
        create_browse_small(global_plot_file, global_plot_file_small)

        # create cloud scene plot files
        cs_plot_file = os.path.join(product_dir, "%s-cloud_scene.browse.png" % product_id)
        plot_cloud_scene(merged_file, cs_plot_file)
        cs_plot_file_small = os.path.join(product_dir, "%s-cloud_scene.browse_small.png" % product_id)
        create_browse_small(cs_plot_file, cs_plot_file_small)
    except Exception, e:
        with open('_alt_error.txt', 'w') as f:
            f.write("%s\n" % str(e))
        with open('_alt_traceback.txt', 'w') as f:
            f.write("%s\n" % traceback.format_exc())
        if os.path.exists(product_dir):
            shutil.rmtree(product_dir)
        raise

    # write metadata file
    metadata_file = os.path.join(product_dir, "%s.met.json" % product_id)
    with open(metadata_file, 'w') as f:
        json.dump(measures_airs.get_metadata(matchup_file, '', 'WVCC_MERGED_DATA'), f, indent=2)


if __name__ == "__main__":
    main()
