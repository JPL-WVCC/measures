import os, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import matplotlib.ticker as plticker
#import seaborn as sns
from mpl_toolkits.basemap import Basemap
import matplotlib.cm as cm
from pylab import linspace
from scipy import interpolate
from matplotlib.colors import LinearSegmentedColormap
from netCDF4 import Dataset
from PIL import Image


def cmap_discretize(cmap, n):
    """Return a discrete colormap from the continuous colormap cmap.
    
        cmap: colormap instance, eg. cm.jet. 
        n: number of colors.
    
    Example
        x = resize(arange(100), (5,100))
        djet = cmap_discretize(cm.jet, 5)
        imshow(x, cmap=djet)
    """

    cdict = cmap._segmentdata.copy()
    # n colors
    colors_i = linspace(0,1.,n)
    # n+1 indices
    indices = linspace(0,1.,n+1)
    for key in ('red','green','blue'):
        # Find the n colors
        D = np.array(cdict[key])
        I = interpolate.interp1d(D[:,0], D[:,1])
        colors = I(colors_i)
        # Place these colors at the correct indices.
        A = np.zeros((n+1,3), float)
        A[:,0] = indices
        A[1:,1] = colors
        A[:-1,2] = colors
        # Create a tuple for the dictionary.
        L = []
        for l in A:
            L.append(tuple(l))
        cdict[key] = tuple(L)
    # Return colormap object.
    return LinearSegmentedColormap('colormap',cdict,1024)


def plot_airs_cloudsat_matchup(matchup_file, plot_file, map_global=False):
    """Generate matchup plot of AIRS-CloudSat."""

    nc = Dataset(matchup_file)
    fig = plt.figure(figsize=(15, 10))
    lon_cs = nc.variables['lon_cs'][:] 
    lat_cs = nc.variables['lat_cs'][:] 
    lon_airs = nc.variables['lon_airs'][:] 
    lat_airs = nc.variables['lat_airs'][:] 
    lon_amsu = nc.variables['lon_amsu'][:] 
    lat_amsu = nc.variables['lat_amsu'][:] 
    airs_nbc = nc.NORTHBOUNDINGCOORDINATE
    airs_sbc = nc.SOUTHBOUNDINGCOORDINATE
    airs_wbc = nc.WESTBOUNDINGCOORDINATE
    airs_ebc = nc.EASTBOUNDINGCOORDINATE

    #print lon_cs, lat_cs, lon_airs, lat_airs, lon_amsu, lat_amsu
    #print airs_nbc, airs_sbc, airs_wbc, airs_ebc

    # handle wrap around
    if abs(airs_ebc - airs_wbc) > 180.:
        wrap = True
        wrap_add = 360.
        airs_ebc += wrap_add
        lon_cs[lon_cs < 0.] += wrap_add
        lon_airs[lon_airs < 0.] += wrap_add
        lon_amsu[lon_amsu < 0.] += wrap_add
    else:
        wrap = False
        wrap_add = 0.

    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    #m.drawlsmask(land_color='#8D7254',ocean_color='#1B457F',lakes=True)
    m.drawmapboundary(fill_color='#1B457F')
    m.fillcontinents(color='#8D7254', lake_color='#1B457F', zorder=0)

    # draw AIRS granule polygon
    bbox_lats = [airs_sbc, airs_nbc, airs_nbc, airs_sbc] 
    bbox_lons = [airs_wbc, airs_wbc, airs_ebc, airs_ebc] 
    x, y = m(bbox_lons, bbox_lats)
    xy = zip(x, y)
    if map_global: facecolor = 'red'
    else: facecolor = None
    poly = Polygon(xy, edgecolor='red', facecolor=facecolor, alpha=0.4)
    plt.gca().add_patch(poly)

    # plot matchups
    if map_global:
        cs_size, amsu_size, airs_size = .5, 1., .75
    else: cs_size, amsu_size, airs_size = 1., 5., 3. 
    cs_plot = m.scatter(lon_cs, lat_cs, marker='d', s=cs_size, c="b", edgecolors='none')
    amsu_plot = m.scatter(lon_amsu, lat_amsu, marker='d', s=amsu_size, c="r", edgecolors='none')
    airs_plot = m.scatter(lon_airs, lat_airs, marker='d', s=airs_size, c="k", edgecolors='none')

    # finish rest of plot
    plt.title("Matched AMSU/AIRS/CloudSat footprints for %s" % os.path.basename(matchup_file))
    if not map_global:
        plt.legend([amsu_plot, cs_plot, airs_plot], ['AMSU', 'CS', 'AIRS'])
    fig.savefig(plot_file)
    plt.close(fig)


def plot_airs_cloudsat_calipso_matchup(matchup_file, plot_file, map_global=False):
    """Generate matchup plot of AIRS-CloudSat-CALIPSO."""

    nc = Dataset(matchup_file)
    fig = plt.figure(figsize=(15, 10))
    lon_cs = nc.variables['lon_cs'][:] 
    lat_cs = nc.variables['lat_cs'][:] 
    lon_airs = nc.variables['lon_airs'][:] 
    lat_airs = nc.variables['lat_airs'][:] 
    lon_amsu = nc.variables['lon_amsu'][:] 
    lat_amsu = nc.variables['lat_amsu'][:] 
    lon_cal = nc.variables['lon_cal'][:] 
    lat_cal = nc.variables['lat_cal'][:] 
    airs_nbc = nc.NORTHBOUNDINGCOORDINATE
    airs_sbc = nc.SOUTHBOUNDINGCOORDINATE
    airs_wbc = nc.WESTBOUNDINGCOORDINATE
    airs_ebc = nc.EASTBOUNDINGCOORDINATE

    # handle wrap around
    if abs(airs_ebc - airs_wbc) > 180.:
        wrap = True
        wrap_add = 360.
        airs_ebc += wrap_add
        lon_cs[lon_cs < 0.] += wrap_add
        lon_airs[lon_airs < 0.] += wrap_add
        lon_amsu[lon_amsu < 0.] += wrap_add
        lon_cal[lon_cal < 0.] += wrap_add
    else:
        wrap = False
        wrap_add = 0.

    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    #m.drawlsmask(land_color='#8D7254',ocean_color='#1B457F',lakes=True)
    m.drawmapboundary(fill_color='#1B457F')
    m.fillcontinents(color='#8D7254', lake_color='#1B457F', zorder=0)

    # draw AIRS granule polygon
    bbox_lats = [airs_sbc, airs_nbc, airs_nbc, airs_sbc] 
    bbox_lons = [airs_wbc, airs_wbc, airs_ebc, airs_ebc] 
    x, y = m(bbox_lons, bbox_lats)
    xy = zip(x, y)
    if map_global: facecolor = 'red'
    else: facecolor = None
    poly = Polygon(xy, edgecolor='red', facecolor=facecolor, alpha=0.4)
    plt.gca().add_patch(poly)

    # plot matchups
    if map_global:
        cs_size, amsu_size, airs_size, cal_size = .5, 1., .75, .3
    else: cs_size, amsu_size, airs_size, cal_size = 10., 7., 5., 1.
    cs_plot = m.scatter(lon_cs, lat_cs, marker='d', s=cs_size, c="b", edgecolors='none')
    cal_plot = m.scatter(lon_cal, lat_cal, marker='d', s=cal_size, c="y", edgecolors='none')
    airs_plot = m.scatter(lon_airs, lat_airs, marker='d', s=airs_size, c="k", edgecolors='none')
    amsu_plot = m.scatter(lon_amsu, lat_amsu, marker='d', s=amsu_size, c="r", edgecolors='none')

    # finish rest of plot
    plt.title("Matched AMSU/AIRS/CloudSat/CALIPSO footprints for %s" % os.path.basename(matchup_file))
    if not map_global:
        plt.legend([cs_plot, cal_plot, airs_plot, amsu_plot], ['CS', 'CAL', 'AIRS', 'AMSU'])
    fig.savefig(plot_file)
    plt.close(fig)


def plot_cloud_scene(merged_file, plot_file):
    """Generate cloud scene plot of AIRS-CloudSat."""

    nc = Dataset(merged_file)
    fig = plt.figure()
    fig.clf()
    cloud_scen = nc.groups['CloudSat'].groups['AIRS_resolution'].groups['2B-CLDCLASS'].variables['cloud_scenario'][:]
    height = nc.groups['CloudSat'].groups['AIRS_resolution'].groups['2B-CLDCLASS'].variables['Height'][:]
    csLat = nc.groups['CloudSat'].groups['AIRS_resolution'].groups['2B-CLDCLASS'].variables['Latitude'][:]
    #radiances = nc.groups['AIRS'].groups['AIRS_resolution'].groups['L1B_AIRS_Science'].variables['radiances'][:]
    #l1bLat = nc.groups['AIRS'].groups['AIRS_resolution'].groups['L1B_AIRS_Science'].variables['Latitude'][:]
    
    #get cloud_scenario data values range
    cloud_scen_range = list(set(cloud_scen.flatten().tolist()))
    cloud_scen_range.sort()
    #print cloud_scen_range
    #print [np.binary_repr(i, 16) for i in cloud_scen_range]
    
    #get cloudsat latitude values range
    csLat_range = list(set(csLat.flatten().tolist()))
    csLat_range.sort()
    #print csLat_range
    
    #build cloudsat lat array with same shape as cloud_scenario
    newCsLat = np.zeros(cloud_scen.shape)
    for i in range(newCsLat.shape[2]): newCsLat[:,:,i] = csLat
    
    #print csLat.shape, height.shape, cloud_scen.shape, newCsLat.shape
    #print csLat.min(), csLat.max()
    #print height.min(), height.max()
    #print cloud_scen.min(), cloud_scen.max()
    ##print newCsLat
    #print type(cloud_scen[0,0,0]), type(cloud_scen[0,0,0].astype('uint16'))
    #print cloud_scen[0,0,0], cloud_scen[0,0,0].astype('uint16')
    
    #get cloud type bits (bits 1-4, little-endian)
    cloud_scen_shift = np.right_shift(np.array(cloud_scen), 1) & int('1111', 2)
    #print cloud_scen_shift
    #cloud_scen_shift_range = list(set(cloud_scen_shift.flatten().tolist()))
    #cloud_scen_shift_range.sort()
    #print cloud_scen_shift_range
    #print [np.binary_repr(i, 4) for i in cloud_scen_shift.flatten()]
    
    cloudTypes = {
        '0000': 'clear',
        '0001': 'Ci',
        '0010': 'As',
        '0011': 'Ac',
        '0100': 'St',
        '0101': 'Sc',
        '0110': 'Cu',
        '0111': 'Ns',
        '1000': 'DC'
    }
    
    #plot
    sp = fig.add_subplot(111)
    csPlot = sp.scatter(newCsLat.flatten(), height.flatten(), 
                        c=cloud_scen_shift.flatten(), 
                        vmin=int('0000', 2), 
                        vmax=int('1000', 2), 
                        edgecolors='none',
                        cmap=cmap_discretize(cm.gist_ncar_r, 9))
                        #cmap=cmap_discretize(sns.blend_palette(["ghostwhite", "mediumseagreen", "#4168B7"], 9, as_cmap=True), 9))
    
    #plot cloudsat latitude values
    #ht = np.zeros(l1bLat.shape)
    #ht += 25000
    #l1bLatPlot = sp.scatter(l1bLat.flatten(), ht.flatten(), edgecolors='none', c='r')
    
    #set x(lat) and y(height) limits
    if csLat.max() > 90: sp.set_xlim(csLat.min(), csLat_range[-2])
    else: sp.set_xlim(csLat.min(), csLat.max())
    sp.set_ylim(0, height.max())
    
    #set plot attrs
    sp.set_xlabel('CloudSat Latitude')
    sp.set_ylabel('CloudSat Height (m)')
    plt.title("Cloud Scene")
    cb = plt.colorbar(csPlot, ticks=range(9)) #set ticks
    cb.ax.set_yticklabels([cloudTypes[np.binary_repr(i, 4)] for i in range(9)]) #set tick labels
    
    #write file
    fig.savefig(plot_file)
    plt.close(fig)


def plot_airs_modis_matchup(matchup_file, plot_file, map_global=False):
    """Generate matchup plot of AIRS-MODIS."""

    nc = Dataset(matchup_file)
    fig = plt.figure(figsize=(15, 10))
    lon_airs = nc.variables['Longitude_Point'][:]
    lat_airs = nc.variables['Latitude_Point'][:]
    airs_nbc = nc.NORTHBOUNDINGCOORDINATE
    airs_sbc = nc.SOUTHBOUNDINGCOORDINATE
    airs_wbc = nc.WESTBOUNDINGCOORDINATE
    airs_ebc = nc.EASTBOUNDINGCOORDINATE

    #print lon_airs, lat_airs
    #print airs_nbc, airs_sbc, airs_wbc, airs_ebc

    # handle wrap around
    #if abs(airs_ebc - airs_wbc) > 180.:
    #    wrap = True
    #    wrap_add = 360.
    #    airs_ebc += wrap_add
    #    lon_airs[lon_airs < 0.] += wrap_add
    #else:
    #    wrap = False
    #    wrap_add = 0.
    wrap = False
    wrap_add = 0.

    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    #m.drawlsmask(land_color='#8D7254',ocean_color='#1B457F',lakes=True)
    m.drawmapboundary(fill_color='#1B457F')
    m.fillcontinents(color='#8D7254', lake_color='#1B457F', zorder=0)

    # draw AIRS granule polygon
    #bbox_lats = [airs_sbc, airs_nbc, airs_nbc, airs_sbc] 
    #bbox_lons = [airs_wbc, airs_wbc, airs_ebc, airs_ebc] 
    #x, y = m(bbox_lons, bbox_lats)
    #xy = zip(x, y)
    #if map_global: facecolor = 'red'
    #else: facecolor = None
    #poly = Polygon(xy, edgecolor='red', facecolor=facecolor, alpha=0.4)
    #plt.gca().add_patch(poly)

    # plot matchups
    if map_global:
        cs_size, amsu_size, airs_size = .5, 1., .75
    else: cs_size, amsu_size, airs_size = 1., 5., 3. 
    airs_plot = m.scatter(lon_airs, lat_airs, marker='d', s=airs_size, c="k", edgecolors='none')

    # finish rest of plot
    plt.title("Matched AIRS/MODIS footprints for %s" % os.path.basename(matchup_file))
    if not map_global:
        plt.legend([airs_plot], ['AIRS'])
    fig.savefig(plot_file)
    plt.close(fig)
    

def plot_airs_modis_amsre_matchup(airs_modis_ds, amsre_grid, matchup_grid, plot_file, map_global=True):
    """Generate matchup plot of AIRS/MODIS/AMSR-E."""

    #fig = plt.figure(figsize=(15, 10))
    fig = plt.figure(figsize=(100, 70))
    lon_airs = airs_modis_ds.variables['Longitude_Point'][:]
    lat_airs = airs_modis_ds.variables['Latitude_Point'][:]
    airs_nbc = airs_modis_ds.NORTHBOUNDINGCOORDINATE
    airs_sbc = airs_modis_ds.SOUTHBOUNDINGCOORDINATE
    airs_wbc = airs_modis_ds.WESTBOUNDINGCOORDINATE
    airs_ebc = airs_modis_ds.EASTBOUNDINGCOORDINATE
    lat_amsre = amsre_grid[:, 0]
    lon_amsre = amsre_grid[:, 1]
    lat_match = matchup_grid[:, 0]
    lon_match = matchup_grid[:, 1]

    wrap = False
    wrap_add = 0.

    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    #m.drawlsmask(land_color='#8D7254',ocean_color='#1B457F',lakes=True)
    #m.drawmapboundary(fill_color='#1B457F')
    #m.fillcontinents(color='#8D7254', lake_color='#1B457F', zorder=0)
    m.drawmapboundary()
    m.fillcontinents(zorder=0)

    # plot matchups
    if map_global:
        amsre_size, airs_size, match_size = 1., 2., 10.
    else: amsre_size, airs_size, match_size = .5, 2., 4.
    match_plot = m.scatter(lon_match, lat_match, marker='d', s=match_size, c="y", edgecolors='none')
    airs_plot = m.scatter(lon_airs, lat_airs, marker='d', s=airs_size, c="r", edgecolors='none')
    amsre_plot = m.scatter(lon_amsre, lat_amsre, marker='d', s=amsre_size, c="k", edgecolors='none')

    # finish rest of plot
    plt.title("Matched AIRS/MODIS/AMSR-E footprints")
    #if not map_global:
    plt.legend([airs_plot, amsre_plot, match_plot], ['AIRS-MODIS', 'AMSR-E', 'matchup'])
    fig.savefig(plot_file)
    plt.close(fig)


def plot_amsre_var(amsre_ds, v, orbit, plot_file, map_global=True):
    """Generate var plot of AMSR-E data."""

    fig = plt.figure(figsize=(15, 10))
    wrap = False
    wrap_add = 0.

    # get lat/lon vals
    amsre_lat = amsre_ds.variables['latitude'][:]
    amsre_lon = amsre_ds.variables['longitude'][:]
    amsre_lon[amsre_lon > 180.] -= 360.

    # print dims of amsre_vars
    amsre_vars = {}
    for i in ('time', 'sst', 'windLF', 'windMF', 'vapor', 'cloud', 'rain', 'land', 'ice', 'nodata'):
        amsre_vars[i] = amsre_ds.variables[i][:]

    # map var
    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    m.drawcoastlines()
    m.drawstates()
    m.drawcountries()
    data1 = np.ma.masked_equal(amsre_vars[v][0 if orbit == 'ascending' else 1], -999.)
    lons, lats = np.meshgrid(amsre_lon, amsre_lat)
    im1 = m.pcolormesh(lons, lats, data1, shading='flat', latlon=True)
    cbar1 = m.colorbar(im1)

    # finish rest of plot
    plt.title("AMSR-E %s for AIRS/MODIS/AMSR-E matchup (%s)" % (v, orbit))
    fig.savefig(plot_file)
    plt.close(fig)


def plot_matched_amsre_var(lats, lons, data, v, plot_file, map_global=True):
    """Generate var plot of AMSR-E data matched to AIRS-MODIS."""

    fig = plt.figure(figsize=(15, 10))
    wrap = False
    wrap_add = 0.

    # map var
    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    m.drawcoastlines()
    m.drawstates()
    m.drawcountries()
    data1 = np.ma.masked_equal(data, -999.)
    im1 = m.pcolormesh(lons, lats, data1, shading='flat', latlon=True)
    cbar1 = m.colorbar(im1)

    # finish rest of plot
    plt.title("AMSR-E %s for AIRS/MODIS/AMSR-E matchup" % v)
    fig.savefig(plot_file)
    plt.close(fig)


def plot_airs_modis_amsr2_matchup(airs_modis_ds, amsr2_grid, matchup_grid, plot_file, map_global=True):
    """Generate matchup plot of AIRS/MODIS/AMSR-2."""

    #fig = plt.figure(figsize=(15, 10))
    fig = plt.figure(figsize=(100, 70))
    lon_airs = airs_modis_ds.variables['Longitude_Point'][:]
    lat_airs = airs_modis_ds.variables['Latitude_Point'][:]
    airs_nbc = airs_modis_ds.NORTHBOUNDINGCOORDINATE
    airs_sbc = airs_modis_ds.SOUTHBOUNDINGCOORDINATE
    airs_wbc = airs_modis_ds.WESTBOUNDINGCOORDINATE
    airs_ebc = airs_modis_ds.EASTBOUNDINGCOORDINATE
    lat_amsr2 = amsr2_grid[:, 0]
    lon_amsr2 = amsr2_grid[:, 1]
    lat_match = matchup_grid[:, 0]
    lon_match = matchup_grid[:, 1]

    wrap = False
    wrap_add = 0.

    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    #m.drawlsmask(land_color='#8D7254',ocean_color='#1B457F',lakes=True)
    #m.drawmapboundary(fill_color='#1B457F')
    #m.fillcontinents(color='#8D7254', lake_color='#1B457F', zorder=0)
    m.drawmapboundary()
    m.fillcontinents(zorder=0)

    # plot matchups
    if map_global:
        amsr2_size, airs_size, match_size = 1., 2., 10.
    else: amsr2_size, airs_size, match_size = .5, 2., 4.
    match_plot = m.scatter(lon_match, lat_match, marker='d', s=match_size, c="y", edgecolors='none')
    airs_plot = m.scatter(lon_airs, lat_airs, marker='d', s=airs_size, c="r", edgecolors='none')
    amsr2_plot = m.scatter(lon_amsr2, lat_amsr2, marker='d', s=amsr2_size, c="k", edgecolors='none')

    # finish rest of plot
    plt.title("Matched AIRS/MODIS/AMSR-2 footprints")
    #if not map_global:
    plt.legend([airs_plot, amsr2_plot, match_plot], ['AIRS-MODIS', 'AMSR-2', 'matchup'])
    fig.savefig(plot_file)
    plt.close(fig)


def plot_amsr2_var(amsr2_ds, v, orbit, plot_file, map_global=True):
    """Generate var plot of AMSR-2 data."""

    fig = plt.figure(figsize=(15, 10))
    wrap = False
    wrap_add = 0.

    # get lat/lon vals
    amsr2_lat = amsr2_ds.variables['latitude'][:]
    amsr2_lon = amsr2_ds.variables['longitude'][:]
    amsr2_lon[amsr2_lon > 180.] -= 360.

    # print dims of amsr2_vars
    amsr2_vars = {}
    for i in ('time', 'sst', 'windLF', 'windMF', 'vapor', 'cloud', 'rain', 'land', 'ice', 'nodata'):
        amsr2_vars[i] = amsr2_ds.variables[i][:]

    # map var
    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    m.drawcoastlines()
    m.drawstates()
    m.drawcountries()
    data1 = np.ma.masked_equal(amsr2_vars[v][0 if orbit == 'ascending' else 1], -999.)
    lons, lats = np.meshgrid(amsr2_lon, amsr2_lat)
    im1 = m.pcolormesh(lons, lats, data1, shading='flat', latlon=True)
    cbar1 = m.colorbar(im1)

    # finish rest of plot
    plt.title("AMSR-2 %s for AIRS/MODIS/AMSR-2 matchup (%s)" % (v, orbit))
    fig.savefig(plot_file)
    plt.close(fig)


def plot_matched_amsr2_var(lats, lons, data, v, plot_file, map_global=True):
    """Generate var plot of AMSR-2 data matched to AIRS-MODIS."""

    fig = plt.figure(figsize=(15, 10))
    wrap = False
    wrap_add = 0.

    # map var
    if map_global:
        m = Basemap(projection='cyl', llcrnrlat=-90., urcrnrlat=90.,
                    llcrnrlon=-180.+wrap_add/2., urcrnrlon=180.+wrap_add/2.,
                    resolution='c', suppress_ticks=False)
    else:
        # handle -90/90 lats
        if airs_sbc < -88.9: sbc = -88.9
        else: sbc = airs_sbc
        if airs_nbc > 88.9: nbc = 88.9
        else: nbc = airs_nbc
        m = Basemap(projection='cyl', llcrnrlat=sbc-1, urcrnrlat=nbc+1,
                    llcrnrlon=airs_wbc-1, urcrnrlon=airs_ebc+1,
                    resolution='c', suppress_ticks=False)
    m.drawcoastlines()
    m.drawstates()
    m.drawcountries()
    data1 = np.ma.masked_equal(data, -999.)
    im1 = m.pcolormesh(lons, lats, data1, shading='flat', latlon=True)
    cbar1 = m.colorbar(im1)

    # finish rest of plot
    plt.title("AMSR-2 %s for AIRS/MODIS/AMSR-2 matchup" % v)
    fig.savefig(plot_file)
    plt.close(fig)


def plot_airs_mls_matchup(nc_file, plot_file, prf_idx=10):
    """Generate AIRS-MLS profile browse."""

    # parse vars
    nc = Dataset(nc_file)
    splice_profile_min = nc.variables['splice_profile_min'][:]
    splice_press = nc.variables['splice_press'][:]
    #print(splice_profile_min.shape)
    #print(splice_press.shape)
    #print(splice_profile_min[prf_idx,:])

    mls_profile = nc.variables['mls_profile'][:]
    mls_press = nc.variables['mls_press'][:]
    #print(mls_profile.shape)
    #print(mls_press.shape)
    #print(mls_profile[prf_idx,:])

    airs_orig_prf = nc.variables['airs_orig_prf'][:]
    airs_orig_pres = nc.variables['airs_orig_pres'][:]
    #print(airs_orig_prf.shape)
    #print(airs_orig_pres.shape)
    #print(airs_orig_prf[prf_idx,:])

    mls_lat = nc.variables['mls_lat'][:]
    mls_lon = nc.variables['mls_lon'][:]

    # plot
    fig = plt.figure()
    fig.clf()
    sp = fig.add_subplot(111, title="Lon: %.3f, Lat: %.3f" % (mls_lon[prf_idx], mls_lat[prf_idx]))
    sp.plot(splice_profile_min[prf_idx,:], splice_press, 'bo-', label="Joined")
    sp.plot(airs_orig_prf[prf_idx,:], airs_orig_pres, 'ro-', label="AIRS")
    sp.plot(mls_profile[prf_idx,:], mls_press, 'go-', label="MLS")
    sp.set_ylim((10, 1000))
    sp.set_xscale("log")
    sp.set_yscale("log")
    sp.set_xlabel("H2O (ppmv)")
    sp.set_ylabel("Pressure (hPa)")
    yticks = [10, 20, 30, 50, 70, 100, 200, 300, 500, 700, 1000]
    sp.yaxis.set_ticks(yticks)
    sp.invert_yaxis()
    sp.yaxis.set_major_formatter(plticker.FormatStrFormatter("%d"))
    sp.yaxis.set_minor_formatter(plticker.FormatStrFormatter("%d"))
    sp.yaxis.grid(True)
    sp.tick_params(axis='both', which='major', labelsize=10)
    sp.tick_params(axis='both', which='minor', labelsize=10)
    sp.legend()
    fig.savefig(plot_file)
    plt.close(fig)


def create_browse_small(browse_file, browse_small_file):
    """Generate small browse image."""

    #img = Image.open(browse_file)
    #img = img.resize((240,240), Image.ANTIALIAS)
    #img.save(browse_small_file, quality=95)
    #img.save(browse_small_file, optimize=True, quality=95)
    os.system("convert -resize 240x240 %s %s" % (browse_file, browse_small_file))
    return True
