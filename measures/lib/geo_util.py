#!/usr/bin/env python
import os, logging
from osgeo import gdal, ogr
import numpy as np
from scipy.spatial import ConvexHull


gdal.UseExceptions()


log_format = "[%(asctime)s: %(levelname)s/%(name)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
logger = logging.getLogger(os.path.splitext(os.path.basename(__file__))[0])


def get_gdal_ds(file):
    """Return GDAL dataset."""

    return gdal.Open(file)


def get_geocoded_coords(ds):
    """Return geocoded coordinates of radar pixels."""

    # extract geo-coded corner coordinates
    gt = ds.GetGeoTransform()
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    lon_arr = list(range(0, cols))
    lat_arr = list(range(0, rows))
    lons = np.empty((cols,))
    lats = np.empty((rows,))
    #logger.info("lon_arr: %s" % lon_arr)
    #logger.info("lat_arr: %s" % lat_arr)
    for py in lat_arr: lats[py] = gt[3] + (py * gt[5])
    for px in lon_arr: lons[px] = gt[0] + (px * gt[1])
    return lats, lons


def get_raster_convex_hull(ds, band_num, nodata=None):
    """Return convex hull vertices."""

    band = ds.GetRasterBand(band_num)
    lats, lons = get_geocoded_coords(ds)
    coords =  np.dstack(np.meshgrid(lons, lats))
    if nodata is not None: # filter out nodata
        coords = coords[band.ReadAsArray() != nodata]
    hull = ConvexHull(coords)
    pts = [list(pt) for pt in hull.points[hull.vertices]]
    pts.append(pts[0])
    return pts
