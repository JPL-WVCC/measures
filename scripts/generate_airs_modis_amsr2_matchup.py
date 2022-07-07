#!/usr/bin/env python
import os, sys, re, logging, json, requests, shutil, argparse
from datetime import datetime
import numpy as np
from netCDF4 import Dataset

from measures import app
from measures.lib.amsr2 import get_amsr2_dataset, best_match
from measures.lib.plot import (plot_airs_modis_amsr2_matchup, 
plot_amsr2_var, plot_matched_amsr2_var, create_browse_small)


logging.basicConfig(level=logging.DEBUG)


AIRS_MODIS_RE = re.compile(r'index-airs.aqua_modis.aqua-(v.*?)-(\d{4})\.(\d{2})\.(\d{2})\.(\d{4})\.nc4')


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

    search_url = '%s/%s/_search' % (app.config['ES_URL'], app.config['AIRS_MODIS_AMSR2_INDEX'])
    r = requests.post(search_url, data=json.dumps(query))
    if r.status_code != 200:
        app.logger.error("Failed to query %s:\n%s" % (search_url, r.text))
        app.logger.error("query: %s" % json.dumps(query, indent=2))
        app.logger.error("returned: %s" % r.text)
    if r.status_code == 200:
        result = r.json()
        total = result['hits']['total']
    else:
        if r.status_code == 404:
            app.logger.warn("Index doesn't exist. Continuing on.")
            result = []
            total = 0
        else: r.raise_for_status()
    #pprint(result)
    return total > 0


def main(amsr2_file, airs_modis_file, airs_modis_met, plot_file, map_global):
    """Main."""

    # extract date/time
    match = AIRS_MODIS_RE.search(airs_modis_file)
    if not match:
        raise RuntimeError("Failed to match input AIRS-MODIS matchup index file.")
    am_vers, yy, mm, dd, tt = match.groups()

    # get product ID
    product_id = "index-airs.aqua_modis.aqua_amsr2.aqua-v%s-%s.%s.%s.%s" % (
        app.config['AIRS_MODIS_AMSR2_VERSION'], yy, mm, dd, tt)

    # check if already exists
    if product_exists(product_id):
        print ("Product %s already exists." % product_id)
        sys.exit(0)

    # get product directory
    product_dir = product_id
    if not os.path.isdir(product_dir):
        os.makedirs(product_dir)

    # read in AMSR-2
    amsr2_ds = get_amsr2_dataset(amsr2_file)
    #logger.info("amsr2_ds: %s" % amsr2_ds)

    # read in AIRS-MODIS index file
    airs_modis_ds = Dataset(airs_modis_file)
    #logger.info("airs_modis_ds: %s" % airs_modis_ds)

    # get matchups
    amsr2_grid, dists, matchup_idx = best_match(amsr2_ds, airs_modis_ds)

    # get matched AMSR-2 lat/lons
    app.logger.info("am_lats: %s" % airs_modis_ds.variables['Latitude_Point'])
    app.logger.info("am_lats.shape: %s" % (airs_modis_ds.variables['Latitude_Point'].shape,))
    matched_amsr2_lats = amsr2_ds.variables['latitude'][matchup_idx[:, :, 1]]
    app.logger.info("matched_amsr2_lats: %s" % matched_amsr2_lats)
    app.logger.info("matched_amsr2_lats.shape: %s" % (matched_amsr2_lats.shape,))
    app.logger.info("am_lons: %s" % airs_modis_ds.variables['Longitude_Point'])
    app.logger.info("am_lons.shape: %s" % (airs_modis_ds.variables['Longitude_Point'].shape,))
    matched_amsr2_lons = amsr2_ds.variables['longitude'][(matchup_idx[:, :, 2])]
    matched_amsr2_lons[matched_amsr2_lons > 180.] -= 360.
    app.logger.info("matched_amsr2_lons: %s" % matched_amsr2_lons)
    app.logger.info("matched_amsr2_lons.shape: %s" % (matched_amsr2_lons.shape,))
    matchup_grid = np.dstack([matched_amsr2_lats.ravel(), matched_amsr2_lons.ravel()])[0]

    # print dims of amsr2_vars
    matched_vars = {}
    for i in ('time', 'sst', 'windLF', 'windMF', 'vapor', 'cloud', 'rain', 'land', 'ice', 'nodata'):
        amsr2_var = amsr2_ds.variables[i][:]
        app.logger.info("amsr2_%s.shape: %s" % (i, amsr2_var.shape))
        matched_vars[i] = amsr2_var[matchup_idx[:, :, 0], matchup_idx[:, :, 1], matchup_idx[:, :, 2]]
        app.logger.info("matched_var[%s]: %s" % (i, matched_vars[i]))
        app.logger.info("matched_var[%s].shape: %s" % (i, matched_vars[i].shape))

    # create matchup file
    match_file = os.path.join(product_dir, "%s.nc4" % product_id)
    root_grp = Dataset(match_file, 'w')
    root_grp.CREATOR = "Gerald Manipon <gmanipon@jpl.nasa.gov>"
    root_grp.COGNIZANT_ENGINEER = "Gerald Manipon <gmanipon@jpl.nasa.gov>"
    root_grp.VERSION = app.config['AIRS_MODIS_AMSR2_VERSION']
    root_grp.PRODUCTIONDATE = "%sZ" % datetime.utcnow().isoformat('T').split('.')[0]
    #root_grp.IDENTIFIER_PRODUCT_DOI = MYD_MATCHUP_INFO['doi']
    root_grp.IDENTIFIER_PRODUCT_DOI_AUTHORITY = "http://dx.doi.org/"
    root_grp.INPUT_AIRS_MODIS_FILE = os.path.basename(airs_modis_file)
    root_grp.INPUT_RSS_AMSR2_FILE = os.path.basename(amsr2_file)
    orb_dim = root_grp.createDimension('orbit_segment', amsr2_ds.dimensions['orbit_segment'])  
    y_dim = root_grp.createDimension('AIRSY', matchup_idx.shape[0])
    x_dim = root_grp.createDimension('AIRSX', matchup_idx.shape[1])
    row_point = root_grp.createVariable('Row_Point', matchup_idx.dtype, ('AIRSY', 'AIRSX'), zlib=True)
    row_point.long_name = "matchup AMSR-2 row index"
    col_point = root_grp.createVariable('Column_Point', matchup_idx.dtype, ('AIRSY', 'AIRSX'), zlib=True)
    col_point.long_name = "matchup AMSR-2 column index"
    orb_point = root_grp.createVariable('Orb_Point', matchup_idx.dtype, ('AIRSY', 'AIRSX'), zlib=True)
    orb_point.long_name = "matchup AMSR-2 orbit index"
    lat_point = root_grp.createVariable('Latitude_Point', matched_amsr2_lats.dtype, ('AIRSY', 'AIRSX'), zlib=True)
    lat_point.long_name = "AMSR-2 latitude"
    lat_point.description = "AMSR-2 latitude"
    lon_point = root_grp.createVariable('Longitude_Point', matched_amsr2_lons.dtype, ('AIRSY', 'AIRSX'), zlib=True)
    lon_point.long_name = "AMSR-2 longitude"
    lon_point.description = "AMSR-2 longitude"
    matched_nc_vars = {}
    for i in ('time', 'sst', 'windLF', 'windMF', 'vapor', 'cloud', 'rain', 'land', 'ice', 'nodata'):
        app.logger.info("%s dtype: %s" % (i, matched_vars[i].dtype))
        dtype = 'b' if i in ('land', 'ice', 'nodata') else matched_vars[i].dtype
        amsr2_var_point = root_grp.createVariable(i, dtype, ('AIRSY', 'AIRSX'), zlib=True)
        amsr2_var_point.long_name = amsr2_ds.variables[i].long_name
        amsr2_var_point.description = amsr2_ds.variables[i].long_name
        amsr2_var_point.units = amsr2_ds.variables[i].units
        try:
            amsr2_var_point.valid_min = amsr2_ds.variables[i].valid_min
            amsr2_var_point.valid_max = amsr2_ds.variables[i].valid_max
        except: pass
        matched_nc_vars[i] = amsr2_var_point
    orb_point[:] = matchup_idx[:, :, 0]
    row_point[:] = matchup_idx[:, :, 1]
    col_point[:] = matchup_idx[:, :, 2]
    lat_point[:] = matched_amsr2_lats
    lon_point[:] = matched_amsr2_lons
    for i in ('time', 'sst', 'windLF', 'windMF', 'vapor', 'cloud', 'rain', 'land', 'ice', 'nodata'):
        matched_nc_vars[i][:] = matched_vars[i]
    root_grp.close()
    
    # create matchup plot
    plot_file = args.plot_file if args.plot_file is not None else os.path.join(product_dir, "%s.browse.png" % product_id)
    plot_airs_modis_amsr2_matchup(airs_modis_ds, amsr2_grid, matchup_grid, plot_file, map_global=map_global)
    plot_file_small = os.path.join(product_dir, "%s.browse_small.png" % product_id)
    create_browse_small(plot_file, plot_file_small)

    # create var plots
    #plot_file2 = os.path.join(product_dir, "%s.all.asc.cloud.browse.png" % product_id)
    #plot_amsr2_var(amsr2_ds, "cloud", "ascending", plot_file2, map_global=True)
    #plot_file_small2 = os.path.join(product_dir, "%s.all.asc.cloud.browse_small.png" % product_id)
    #create_browse_small(plot_file2, plot_file_small2)
    #plot_file3 = os.path.join(product_dir, "%s.all.desc.cloud.browse.png" % product_id)
    #plot_amsr2_var(amsr2_ds, "cloud", "descending", plot_file3, map_global=True)
    #plot_file_small3 = os.path.join(product_dir, "%s.all.desc.cloud.browse_small.png" % product_id)
    #create_browse_small(plot_file3, plot_file_small3)
    plot_file4 = os.path.join(product_dir, "%s.cloud.browse.png" % product_id)
    plot_matched_amsr2_var(matched_amsr2_lats, matched_amsr2_lons, matched_vars["cloud"], 
                           "cloud", plot_file4, map_global=True)
    plot_file_small4 = os.path.join(product_dir, "%s.cloud.browse_small.png" % product_id)
    create_browse_small(plot_file4, plot_file_small4)

    # write metadata file
    with open(airs_modis_met) as f:
        met = json.load(f)
    met['data_product_name'] = "WVCC_AIRS_MDS_AMSR2_IND"
    metadata_file = os.path.join(product_dir, "%s.met.json" % product_id)
    with open(metadata_file, 'w') as f:
        json.dump(met, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Matchup AMSR-2 to AIRS-MODIS pixels.")
    parser.add_argument("--amsr2_file", help="gzipped RSS AMSR-2 daily file",
                        default="f32_20020715v7.gz")
    parser.add_argument("--airs_modis_file", help="AIRS-MODIS matchup file",
                        default="index-airs.aqua_modis.aqua-v1.0-2003.01.05.0000.nc4")
    parser.add_argument("--airs_modis_met", help="AIRS-MODIS matchup file metatadata JSON file",
                        default="index-airs.aqua_modis.aqua-v1.0-2003.01.05.0000.met.json")
    parser.add_argument("--plot_file", help="output matchup plot file", default=None)
    parser.add_argument("--map_global", help="draw global map", action="store_true",
                        default=False)
    args = parser.parse_args()
    main(args.amsr2_file, args.airs_modis_file, args.airs_modis_met, args.plot_file, args.map_global)
