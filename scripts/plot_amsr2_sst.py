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
from measures.lib.amsr2 import get_amsr2_dataset
from measures.lib.plot import plot_airs_modis_amsr2_matchup, create_browse_small


logging.basicConfig(level=logging.DEBUG)


def main(amsr2_file, v, plot_file, map_global):
    """Main."""

    # read in AMSR-2
    amsr2_ds = get_amsr2_dataset(amsr2_file)
    #logger.info("amsr2_ds: %s" % amsr2_ds)

    # create AMSR-2 grid
    amsr2_lat = amsr2_ds.variables['latitude'][:]
    amsr2_lon = amsr2_ds.variables['longitude'][:]
    amsr2_lon[amsr2_lon > 180.] -= 360.
    app.logger.info("amsr2_lat:  %s" % amsr2_lat)
    app.logger.info("amsr2_lat.shape:  %s" % (amsr2_lat.shape,))
    app.logger.info("amsr2_lon:  %s" % amsr2_lon)
    app.logger.info("amsr2_lon.shape:  %s" % (amsr2_lon.shape,))

    # print dims of amsr2_vars
    amsr2_vars = {}
    for i in ('time', 'sst', 'windLF', 'windMF', 'vapor', 'cloud', 'rain', 'land', 'ice', 'nodata'):
        amsr2_vars[i] = amsr2_ds.variables[i][:]
        app.logger.info("amsr2_%s.shape: %s" % (i, amsr2_vars[i].shape))

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
    data1 = np.ma.masked_equal(amsr2_vars[v][0], -999.)
    app.logger.info("data1:  %s" % data1)
    app.logger.info("data1.shape:  %s" % (data1.shape,))
    data2 = np.ma.masked_equal(amsr2_vars[v][1], -999.)
    app.logger.info("data2:  %s" % data2)
    app.logger.info("data2.shape:  %s" % (data2.shape,))
    lons, lats = np.meshgrid(amsr2_lon, amsr2_lat)
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
    parser = argparse.ArgumentParser(description="Plot AMSR-2 data.")
    parser.add_argument("--amsr2_file", help="gzipped RSS AMSR-2 daily file",
                        default="f32_20020715v7.gz")
    parser.add_argument("--variable", help="AMSR-2 variable to plot", default="sst")
    parser.add_argument("--plot_file", help="output matchup plot file", default=None)
    parser.add_argument("--map_global", help="draw global map", action="store_true",
                        default=False)
    args = parser.parse_args()
    main(args.amsr2_file, args.variable, args.plot_file, args.map_global)
