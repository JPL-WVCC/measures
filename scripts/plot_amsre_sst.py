#!/usr/bin/env python
import os, sys, re, logging, json, requests, shutil, argparse
from datetime import datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
#import seaborn as sns
from mpl_toolkits.basemap import Basemap
import matplotlib.cm as cm
from pylab import linspace
from scipy import interpolate
from matplotlib.colors import LinearSegmentedColormap
from netCDF4 import Dataset

from measures import app
from measures.lib.amsre import get_amsre_dataset
from measures.lib.plot import plot_airs_modis_amsre_matchup, create_browse_small


logging.basicConfig(level=logging.DEBUG)


def main(amsre_file, v, plot_file, map_global):
    """Main."""

    # read in AMSR-E
    amsre_ds = get_amsre_dataset(amsre_file)
    #logger.info("amsre_ds: %s" % amsre_ds)

    # create AMSR-E grid
    amsre_lat = amsre_ds.variables['latitude'][:]
    amsre_lon = amsre_ds.variables['longitude'][:]
    amsre_lon[amsre_lon > 180.] -= 360.
    app.logger.info("amsre_lat:  %s" % amsre_lat)
    app.logger.info("amsre_lat.shape:  %s" % (amsre_lat.shape,))
    app.logger.info("amsre_lon:  %s" % amsre_lon)
    app.logger.info("amsre_lon.shape:  %s" % (amsre_lon.shape,))

    # print dims of amsre_vars
    amsre_vars = {}
    for i in ('time', 'sst', 'windLF', 'windMF', 'vapor', 'cloud', 'rain', 'land', 'ice', 'nodata'):
        amsre_vars[i] = amsre_ds.variables[i][:]
        app.logger.info("amsre_%s.shape: %s" % (i, amsre_vars[i].shape))

    # plot var
    wrap = False
    wrap_add = 0.
    fig = plt.figure()
    fig.clf()
    m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                resolution='c', suppress_ticks=False)
    m.drawcoastlines()
    m.drawstates()
    m.drawcountries()
    data1 = np.ma.masked_equal(amsre_vars[v][0], -999.)
    app.logger.info("data1:  %s" % data1)
    app.logger.info("data1.shape:  %s" % (data1.shape,))
    data2 = np.ma.masked_equal(amsre_vars[v][1], -999.)
    app.logger.info("data2:  %s" % data2)
    app.logger.info("data2.shape:  %s" % (data2.shape,))
    lons, lats = np.meshgrid(amsre_lon, amsre_lat)
    app.logger.info("lons:  %s" % lons)
    app.logger.info("lons.shape:  %s" % (lons.shape,))
    app.logger.info("lats:  %s" % lats)
    app.logger.info("lats.shape:  %s" % (lats.shape,))
    im1 = m.pcolormesh(lons, lats, data1, shading='flat', latlon=True)
    im2 = m.pcolormesh(lons, lats, data2, shading='flat', latlon=True)
    cbar1 = m.colorbar(im1)
    #cbar2 = m.colorbar(im2)
    fig.savefig("%s.png" % v if plot_file is None else plot_file)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plot AMSR-E data.")
    parser.add_argument("--amsre_file", help="gzipped RSS AMSR-E daily file",
                        default="f32_20020715v7.gz")
    parser.add_argument("--variable", help="AMSR-E variable to plot", default="sst")
    parser.add_argument("--plot_file", help="output matchup plot file", default=None)
    parser.add_argument("--map_global", help="draw global map", action="store_true",
                        default=False)
    args = parser.parse_args()
    main(args.amsre_file, args.variable, args.plot_file, args.map_global)
