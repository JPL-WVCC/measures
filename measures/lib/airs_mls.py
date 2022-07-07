import os, sys, time, json
from datetime import datetime
from subprocess import check_output, call
from netCDF4 import Dataset
import numpy as np
from scipy.io import loadmat
from pprint import pprint

from prov_es.model import get_uuid, ProvEsDocument

from measures import app
from measures.lib.constants import TAI
from .prov_info import MLS_MATCHUP_INFO


# MLS id template
MLS_ID_TMPL = "MLS-Aura_L2GP-H2O_v04-*_%04d_d%03d"


# AIRS id template
AIRS_ID_TMPL = "AIRS.%04d.%02d.%02d.%03d.L2.RetSup.v6.*"


# matchup var config
MATCHUP_VARS = {
    'airs_match_gran_id': {
        'type': 'i4',
        'description': 'AIRS granule number [1-240]',
    },
    'airs_match_yr_id': {
        'type': 'i4',
        'description': 'AIRS granule year',
    },
    'airs_match_mo_id': {
        'type': 'i4',
        'description': 'AIRS granule month',
    },
    'airs_match_dy_id': {
        'type': 'i4',
        'description': 'AIRS granule day',
    },
    'airs_match_min_tai': {
        'type': 'f8',
        'description': 'TAI timestamp of matched AIRS pixel',
        'units': 'seconds since 1993-01-01T00:00:00Z',
    },
    'mls_time': {
        'type': 'f8',
        'description': 'TAI timestamp of matched MLS pixel',
        'units': 'seconds since 1993-01-01T00:00:00Z',
    },
}


# joined var config
JOINED_VARS = {
    'airs_lat2_aft': {
        'type': 'f8',
        'description': 'AIRS Latitude 1 footprint after airs_lat2_min',
        'units': 'degrees',
    },
    'airs_lat2_bef': {
        'type': 'f8',
        'description': 'AIRS Latitude 1 footprint before airs_lat2_min',
        'units': 'degrees',
    },
    'airs_lat2_min': {
        'type': 'f8',
        'description': 'AIRS Latitude closest to MLS',
        'units': 'degrees',
    },
    'airs_lon2_aft': {
        'type': 'f8',
        'description': 'AIRS Longitude 1 footprint after airs_lon2_min',
        'units': 'degrees',
    },
    'airs_lon2_bef': {
        'type': 'f8',
        'description': 'AIRS Longitude 1 footprint before airs_lon2_min',
        'units': 'degrees',
    },
    'airs_lon2_min': {
        'type': 'f8',
        'description': 'AIRS Longitude closest to MLS',
        'units': 'degrees',
    },
    'airs_orig_prf': {
        'type': 'f8',
        'description': 'AIRS original H2O profiles',
        'units': 'ppmv',
    },
    'airs_profile_aft': {
        'type': 'f8',
        'description': 'AIRS H2O profiles by using 1 footprint after the closest AIRS to MLS',
        'units': 'ppmv',
    },
    'airs_profile_bef': {
        'type': 'f8',
        'description': 'AIRS H2O profiles by using 1 footprint before the closest AIRS to MLS',
        'units': 'ppmv',
    },
    'airs_profile_min': {
        'type': 'f8',
        'description': 'AIRS H2O profiles by using the closest AIRS to MLS',
        'units': 'ppmv',
    },
    'mls_lat': {
        'type': 'f8',
        'description': 'MLS Latitude',
        'units': 'degrees',
    },
    'mls_lon': {
        'type': 'f8',
        'description': 'MLS Longitude',
        'units': 'degrees',
    },
    'mls_profile': {
        'type': 'f8',
        'description': 'MLS H2O profiles',
        'units': 'ppmv',
    },
    'splice_profile_aft': {
        'type': 'f8',
        'description': 'Joined H2O profiles by using 1 footprint after the closest AIRS to MLS',
        'units': 'ppmv',
    },
    'splice_profile_bef': {
        'type': 'f8',
        'description': 'Joined H2O profiles by using 1 footprint before the closest AIRS to MLS',
        'units': 'ppmv',
    },
    'splice_profile_min': {
        'type': 'f8',
        'description': 'Joined H2O profiles by using the closest AIRS to MLS',
        'units': 'ppmv',
    },
    'temp_aft': {
        'type': 'f8',
        'description': 'Joined temperature profiles by using AIRS footprint after the closest',
        'units': 'K',
    },
    'temp_bef': {
        'type': 'f8',
        'description': 'Joined temperature profiles by using AIRS footprint before the closest',
        'units': 'K',
    },
    'temp_min': {
        'type': 'f8',
        'description': 'Joined temperature profiles by using the closest AIRS to MLS',
        'units': 'K',
    },
}


def convert(mat_file, joined_file, nc4_file):
    """Convert AIRS-MLS matchup and joined MAT-files to NetCDF4."""

    # open matchup matlab file
    mat_dict = loadmat(mat_file)
    #for var in sorted(mat_dict):
    #    if isinstance(mat_dict[var], np.ndarray):
    #        print("%s %s with shape %s" % (var, type(mat_dict[var]), mat_dict[var].shape))
    #    else:
    #        print("%s %s: %s" % (var, type(mat_dict[var]), mat_dict[var]))

    # open joined matlab file
    joined_dict = loadmat(joined_file)
    #for var in sorted(joined_dict):
    #    if isinstance(joined_dict[var], np.ndarray):
    #        print("%s %s with shape %s" % (var, type(joined_dict[var]), joined_dict[var].shape))
    #    else:
    #        print("%s %s: %s" % (var, type(joined_dict[var]), joined_dict[var]))

    # mask invalid values
    for i in mat_dict:
        try:
            masked = np.ma.masked_invalid(mat_dict[i])   
            
            # if mls_time, mask where less than 0
            if i == 'mls_time': masked = np.ma.masked_where(masked < 0, masked)

            mat_dict[i] = masked
        except:
            print("Failed to mask %s. Continuing." % i)

    for i in joined_dict:
        try:
            masked = np.ma.masked_invalid(joined_dict[i])   
            joined_dict[i] = masked
        except:
            print("Failed to mask %s. Continuing." % i)

    # write NetCDF file
    root_grp = Dataset(nc4_file, 'w')
    root_grp.CREATOR = "Tao Wang <tao.wang@nasa.gov>"
    root_grp.COGNIZANT_ENGINEER = "Gerald Manipon <gmanipon@jpl.nasa.gov>"
    root_grp.VERSION = app.config['AIRS_MLS_VERSION']
    root_grp.PRODUCTIONDATE = "%sZ" % datetime.utcnow().isoformat('T').split('.')[0]
    root_grp.IDENTIFIER_PRODUCT_DOI = MLS_MATCHUP_INFO['doi']
    root_grp.IDENTIFIER_PRODUCT_DOI_AUTHORITY = "http://dx.doi.org/"

    # add time info
    t = mat_dict['mls_time'][:]
    ti_dt = datetime(*time.gmtime(t.min() + TAI)[0:6])
    startdate, starttime = ti_dt.isoformat('T').split('T')
    root_grp.RANGEBEGINNINGDATE = startdate
    root_grp.RANGEBEGINNINGTIME = starttime
    tf_dt = datetime(*time.gmtime(t.max() + TAI)[0:6])
    enddate, endtime = tf_dt.isoformat('T').split('T')
    root_grp.RANGEENDINGDATE = enddate
    root_grp.RANGEENDINGTIME = endtime

    # add provenance info of MLS and AIRS ids
    mls_id = MLS_ID_TMPL % (ti_dt.year, ti_dt.timetuple().tm_yday)
    root_grp.MLS_GRANULE_ID = mls_id
    airs_ids = {}
    for i, yr in enumerate(mat_dict['airs_match_yr_id']):
        if np.isnan(yr): continue
        airs_id = AIRS_ID_TMPL % (yr, mat_dict['airs_match_mo_id'][i],
                                  mat_dict['airs_match_dy_id'][i],
                                  mat_dict['airs_match_gran_id'][i])
        airs_ids[airs_id] = True
    root_grp.AIRS_GRANULE_IDS = " ".join(sorted(airs_ids))

    # append spatial info
    lat = joined_dict['airs_lat2_min'][:]
    lon = joined_dict['airs_lon2_min'][:]
    root_grp.NORTHBOUNDINGCOORDINATE = lat.max()
    root_grp.SOUTHBOUNDINGCOORDINATE = lat.min()
    root_grp.EASTBOUNDINGCOORDINATE = lon.max()
    root_grp.WESTBOUNDINGCOORDINATE = lon.min()

    # create dimensions and dimension vars
    matchup_dim = root_grp.createDimension('matchup', None)
    airs_idx_dim = root_grp.createDimension('airs_idx_size', 2)
    pres_dim_dict = {}
    pres_dim_dict[joined_dict['airs_orig_pres'].shape[0]] = 'airs_orig_pres'
    root_grp.createDimension('airs_orig_pres', joined_dict['airs_orig_pres'].shape[0])
    airs_orig_pres = root_grp.createVariable('airs_orig_pres', 'f8', ('airs_orig_pres',), zlib=True)
    airs_orig_pres.description = "AIRS original pressure levels"
    airs_orig_pres.units = "hPa"
    airs_orig_pres[:] = joined_dict['airs_orig_pres'][:]
    pres_dim_dict[joined_dict['splice_press'].shape[0]] = 'splice_press'
    root_grp.createDimension('splice_press', joined_dict['splice_press'].shape[0])
    splice_press = root_grp.createVariable('splice_press', 'f8', ('splice_press',), zlib=True)
    splice_press.description = "Pressure levels of joined data"
    splice_press.units = "hPa"
    splice_press[:] = joined_dict['splice_press'][:]
    pres_dim_dict[joined_dict['mls_press'].shape[0]] = 'mls_press'
    root_grp.createDimension('mls_press', joined_dict['mls_press'].shape[0])
    mls_press = root_grp.createVariable('mls_press', 'f8', ('mls_press',), zlib=True)
    mls_press.description = "Pressure of MLS data"
    mls_press.units = "hPa"
    mls_press[:] = joined_dict['mls_press'][:]

    # write matchup indices from match
    airs_match_min_ind = root_grp.createVariable('airs_match_min_ind', 'i4',
                                                 ('matchup', 'airs_idx_size',),
                                                 zlib=True)
    airs_match_min_ind.description = "matchup AIRS index [GeoXTrack, GeoTrack]"
    airs_match_min_ind[:] = mat_dict['airs_match_min_ind'][:] - 1 # decrement since matlab arrays are 1-based
    mls_match_ind = root_grp.createVariable('mls_match_ind', 'i4', ('matchup',), zlib=True)
    mls_match_ind.description = "matchup MLS index"
    mls_match_ind[:] = mat_dict['mls_match_ind'][:] - 1 # decrement since matlab arrays are 1-based

    # write variables from match
    for v in sorted(MATCHUP_VARS):
        cfg = MATCHUP_VARS[v]
        d = mat_dict[v]
        var = root_grp.createVariable(v, cfg['type'], ('matchup',), zlib=True)
        for attr in cfg.keys():
            if attr != 'type': setattr(var, attr, cfg[attr])
        var[:] = d
              
    # write variables from joined
    for v in sorted(JOINED_VARS):
        cfg = JOINED_VARS[v]
        d = joined_dict[v]
        if d.shape[1] == 1: dims = ('matchup',)
        else:
            dims = ('matchup', pres_dim_dict[d.shape[1]],)
        var = root_grp.createVariable(v, cfg['type'], dims, zlib=True)
        for attr in cfg.keys():
            if attr != 'type': setattr(var, attr, cfg[attr])
        var[:] = d

    # close file
    root_grp.close()


def get_metadata(nc_file, tags, dataset='WVCC_AIRS_MLS_IND'):
    """Return dataset and metadata from matchup file for ingestion into GRQ."""

    # get data
    nc = Dataset(nc_file)
    start_time = "%sT%sZ" % (nc.getncattr('RANGEBEGINNINGDATE'),
                             nc.getncattr('RANGEBEGINNINGTIME'))
    end_time = "%sT%sZ" % (nc.getncattr('RANGEENDINGDATE'),
                           nc.getncattr('RANGEENDINGTIME'))
    north = nc.getncattr('NORTHBOUNDINGCOORDINATE').astype(int)
    south = nc.getncattr('SOUTHBOUNDINGCOORDINATE').astype(int)
    west = nc.getncattr('WESTBOUNDINGCOORDINATE').astype(int)
    east = nc.getncattr('EASTBOUNDINGCOORDINATE').astype(int)
    version = nc.getncattr('VERSION')
    lon = np.ma.masked_equal(nc.variables['mls_lon'][:].flatten().astype(int), -9999).compressed()
    lat = np.ma.masked_equal(nc.variables['mls_lat'][:].flatten().astype(int), -9999).compressed()
    coords = [[lon[i], lat[i]] for i in range(len(lon))]

    # return metadata
    return {
        "metadata": {
            "level": "L2",
            "tags": tags.split(),
            "data_product_name": dataset,
            "bbox": [
                [west, south],
                [west, north],
                [east, north],
                [east, south],
                [west, south],
            ]
        },
        "dataset": {
            "version": version,
            "creation_timestamp": datetime.utcnow().isoformat('T'),
            "starttime": start_time,
            "endtime": end_time,
            "location": {
                "type": "polygon",
                "coordinates": [
                    [
                        [west, south],
                        [west, north],
                        [east, north],
                        [east, south],
                        [west, south],
                    ]
                ]
            }
        }
    }
