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
from .amsre_daily_v7 import AMSREdaily
from .constants import (MAJOR_AXIS_RADIUS, MINOR_AXIS_RADIUS,
                        RADIUS_EARTH, DEG2RAD, TAI)


np.set_printoptions(precision=12)


AIRS_RE = re.compile(r'AIRS\.(\d{4})\.(\d{2})\.(\d{2})\.(\d{3}).*$')


def get_amsre_dataset(fname, missing=-999.0):
    """Return AMSR-E dataset object."""
    
    ds = AMSREdaily(fname, missing=missing)
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


def best_match(amsre_ds, airs_modis_ds, bucket="wvcc-atrain-product-bucket"):
    """Find closest AMSR-E pixel to AIRS-MODIS pixel by distance. Return matchup indices
       and distances for these matchups."""

    # create AMSR-E grid
    amsre_lat = amsre_ds.variables['latitude'][:]
    amsre_lon = amsre_ds.variables['longitude'][:]
    amsre_lon[amsre_lon > 180.] -= 360.
    app.logger.info("amsre_lat:  %s" % amsre_lat)
    app.logger.info("amsre_lat.shape:  %s" % (amsre_lat.shape,))
    app.logger.info("amsre_lon:  %s" % amsre_lon)
    app.logger.info("amsre_lon.shape:  %s" % (amsre_lon.shape,))
    amsre_lats, amsre_lons = np.meshgrid(amsre_lat.ravel(), amsre_lon.ravel())
    app.logger.info("amsre_lats:  %s" % amsre_lats)
    app.logger.info("amsre_lats.shape:  %s" % (amsre_lats.shape,))
    app.logger.info("amsre_lons:  %s" % amsre_lons)
    app.logger.info("amsre_lons.shape:  %s" % (amsre_lons.shape,))
    amsre_grid = np.dstack([amsre_lats.ravel(), amsre_lons.ravel()])[0]
    app.logger.info("amsre_grid: %s" % amsre_grid)
    app.logger.info("amsre_grid.shape: %s" % (amsre_grid.shape,))

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
    tree = cKDTree(amsre_grid)
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
        amsre_x, amsre_y = idx%amsre_lat.shape[0], idx//amsre_lat.shape[0]
        amsre_orb = 0 if snt[am_x//3] == "A" else 1
        #app.logger.info("am_x, amy_y: %s %s" % (am_x, am_y))
        #app.logger.info("amsre_orb, amsre_x, amsre_y: %s %s %s" % (amsre_orb, amsre_x, amsre_y))
        matchup_idx[am_x, am_y] = amsre_orb, amsre_x, amsre_y
        #amsre_la, amsre_lo = amsre_grid[idx]      
        #amsre_la2, amsre_lo2 = ( amsre_lat[matchup_idx[am_x, am_y, 0]],
        #                         amsre_lon[matchup_idx[am_x, am_y, 1]] )
        #app.logger.info("AIRS-MODIS/AMSR-E lon/lat: %s %s %s %s %s %s" % (am_lon, am_lat, amsre_lo, amsre_la, amsre_lo2, amsre_la2))
    app.logger.info("matchup_idx: %s" % matchup_idx)
    app.logger.info("matchup_idx.shape: %s" % (matchup_idx.shape,))
    return amsre_grid, dists, matchup_idx
