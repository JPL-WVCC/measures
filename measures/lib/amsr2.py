import os, re, boto3
import numpy as np
import scipy as sp
from netCDF4 import Dataset
from scipy.spatial import cKDTree
from pyhdf.SD import SD, SDC
from pyhdf.HDF import HDF
from pyhdf.VS import VS
from pyhdf.V import V
from pyhdf.error import HDF4Error

import measures
from measures import app
from .amsr2_daily_v7 import AMSR2daily
from .constants import (MAJOR_AXIS_RADIUS, MINOR_AXIS_RADIUS,
                        RADIUS_EARTH, DEG2RAD, TAI)


np.set_printoptions(precision=12)


AIRS_RE = re.compile(r'AIRS\.(\d{4})\.(\d{2})\.(\d{2})\.(\d{3}).*$')


def get_amsr2_dataset(fname, missing=-999.0):
    """Return AMSR-2 dataset object."""
    
    ds = AMSR2daily(fname, missing=missing)
    if not ds.variables:
        raise RuntimeError("Failed to read file %s." % fname)
    return ds


def get_scan_node_type(fname):
    """Return scan_node_type from AIRS RetStd."""

    app.logger.info("fname: %s" % fname)
    hdf = HDF(str(fname))
    vs = hdf.vstart()
    vd = vs.attach('scan_node_type')
    snt = map(lambda x: str(unichr(x[0])), vd[:])
    vd.detach()
    vs.end()
    hdf.close()
    return snt


def best_match(amsr2_ds, airs_modis_ds, bucket="wvcc-atrain-product-bucket"):
    """Find closest AMSR-2 pixel to AIRS-MODIS pixel by distance. Return matchup indices
       and distances for these matchups."""

    # create AMSR-2 grid
    amsr2_lat = amsr2_ds.variables['latitude'][:]
    amsr2_lon = amsr2_ds.variables['longitude'][:]
    amsr2_lon[amsr2_lon > 180.] -= 360.
    app.logger.info("amsr2_lat:  %s" % amsr2_lat)
    app.logger.info("amsr2_lat.shape:  %s" % (amsr2_lat.shape,))
    app.logger.info("amsr2_lon:  %s" % amsr2_lon)
    app.logger.info("amsr2_lon.shape:  %s" % (amsr2_lon.shape,))
    amsr2_lats, amsr2_lons = np.meshgrid(amsr2_lat.ravel(), amsr2_lon.ravel())
    app.logger.info("amsr2_lats:  %s" % amsr2_lats)
    app.logger.info("amsr2_lats.shape:  %s" % (amsr2_lats.shape,))
    app.logger.info("amsr2_lons:  %s" % amsr2_lons)
    app.logger.info("amsr2_lons.shape:  %s" % (amsr2_lons.shape,))
    amsr2_grid = np.dstack([amsr2_lats.ravel(), amsr2_lons.ravel()])[0]
    app.logger.info("amsr2_grid: %s" % amsr2_grid)
    app.logger.info("amsr2_grid.shape: %s" % (amsr2_grid.shape,))

    # get scan_node_type from AIRS granules
    c = boto3.client('s3')
    snt = []
    for i in range(5):
        attr = 'Comp_FileB%d' % i
        if hasattr(airs_modis_ds, attr):
            val = getattr(airs_modis_ds, attr)
            match = AIRS_RE.search(val)
            if not match:
                raise RuntimeError("Failed to extract AIRS granule info from %s" % val)
            #airs_grans.append((match.groups()))
            yr, mo, dy, grn = match.groups()
            prefix = "airs/v6/%s/%s/%s/airx2ret/AIRS.%s.%s.%s.%s" % (yr, mo, dy,
                                                                     yr, mo, dy, grn)
            res = c.list_objects(Bucket=bucket, Prefix=prefix)
            key = res['Contents'][0]['Key']
            f = os.path.basename(key)
            c.download_file(bucket, key, f)
            snt.extend(get_scan_node_type(f))
            try: os.unlink(f)
            except: pass
    snt = np.array(snt)
    app.logger.info("snt: %s" % snt)
    app.logger.info("snt.shape: %s" % (snt.shape,))

    # create (lat, lon) points from AIRS_MODIS
    am_lats = airs_modis_ds.variables['Latitude_Point'][:]
    app.logger.info("am_lats: %s" % am_lats)
    app.logger.info("am_lats.shape: %s" % (am_lats.shape,))
    am_lons = airs_modis_ds.variables['Longitude_Point'][:]
    app.logger.info("am_lons: %s" % am_lons)
    app.logger.info("am_lons.shape: %s" % (am_lons.shape,))
    am_pts = np.dstack([am_lats.ravel(), am_lons.ravel()])[0]
    app.logger.info("am_pts: %s" % am_pts)
    app.logger.info("am_pts.shape: %s" % (am_pts.shape,))

    # get nearest neighbors
    tree = cKDTree(amsr2_grid)
    dists, indexes = tree.query(am_pts)
    app.logger.info("dists: %s" % dists)
    app.logger.info("dists.shape: %s" % (dists.shape,))
    app.logger.info("indexes: %s" % indexes)
    app.logger.info("indexes.shape: %s" % (indexes.shape,))

    # build matchup index
    matchup_idx = np.zeros(shape=(am_lats.shape[0], am_lats.shape[1], 3), dtype=np.int)
    for i, am_loc in enumerate(am_pts[:]):
        am_x, am_y = i//am_lats.shape[1], i%am_lats.shape[1]
        am_lat, am_lon = am_loc
        idx = indexes[i]
        amsr2_x, amsr2_y = idx%amsr2_lat.shape[0], idx//amsr2_lat.shape[0]
        amsr2_orb = 0 if snt[am_x//3] == "A" else 1
        #app.logger.info("am_x, amy_y: %s %s" % (am_x, am_y))
        #app.logger.info("amsr2_orb, amsr2_x, amsr2_y: %s %s %s" % (amsr2_orb, amsr2_x, amsr2_y))
        matchup_idx[am_x, am_y] = amsr2_orb, amsr2_x, amsr2_y
        #amsr2_la, amsr2_lo = amsr2_grid[idx]      
        #amsr2_la2, amsr2_lo2 = ( amsr2_lat[matchup_idx[am_x, am_y, 0]],
        #                         amsr2_lon[matchup_idx[am_x, am_y, 1]] )
        #app.logger.info("AIRS-MODIS/AMSR-2 lon/lat: %s %s %s %s %s %s" % (am_lon, am_lat, amsr2_lo, amsr2_la, amsr2_lo2, amsr2_la2))
    app.logger.info("matchup_idx: %s" % matchup_idx)
    app.logger.info("matchup_idx.shape: %s" % (matchup_idx.shape,))
    return amsr2_grid, dists, matchup_idx
