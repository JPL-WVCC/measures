import os, sys, time, json
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
from pydap.client import open_url
import numpy as np
from pprint import pformat
from datetime import datetime, timedelta
from SOAPpy.WSDL import Proxy
#from numba import jit
from netCDF4 import Dataset
import requests

from prov_es.model import get_uuid, ProvEsDocument

import measures
from measures import app
from .constants import (MAJOR_AXIS_RADIUS, MINOR_AXIS_RADIUS,
                        RADIUS_EARTH, DEG2RAD, TAI)
from .xml import get_etree, get_nsmap
from .fast_utils import best_match as fast_best_match
from .prov_info import (AIRS_GRANULE_RE, CS_GRANULE_RE, AIRS_METADATA_MAP,
CS_METADATA_MAP, ADDITIONAL_NAMESPACES, AIRS_COLLECTION_INFO, 
CLOUDSAT_COLLECTION_INFO, SOFTWARE_INFO, MATCHUP_INFO)


np.set_printoptions(precision=12)


def get_dap_data(ds, var_names):
    """Function to return DAP data that can handle different DAP server installations."""

    for v in var_names:
        if v in ds: return ds[v].data[:]
    raise RuntimeError("Failed to find variables %s." % var_names)


def get_time_info(airs_dap_url):
    """Return dict containing AIRS profile UTC, start and end UTC."""

    ds = open_url(airs_dap_url)
    time_vars = [
        "L2_Standard_atmospheric_surface_product_Geolocation_Fields_Time",
        "Time"
    ]
    prf_time = get_dap_data(ds, time_vars) + TAI
    t = prf_time.reshape((prf_time.shape[0]*prf_time.shape[1]))
    sorted_args = t.argsort()
    start_utc = t[sorted_args[0]]
    # this is actually the start of last pixel;
    # add 6.9999 secs to fill out to the end
    end_utc = t[sorted_args[-1]] + 6.9999
    return { 'profile_utc': prf_time,
             'start_utc': start_utc,
             'end_utc': end_utc }


def grq_cloudsat(start_utc, end_utc):
    """Return list of CloudSat DAP URLs that match to AIRS temporally."""

    # get ISO format
    ti_elts = time.gmtime(start_utc)
    ti_dt = datetime(*ti_elts[0:3]) - timedelta(days=1)
    starttime = ti_dt.isoformat('T')
    app.logger.debug(ti_dt)
    tf_elts = time.gmtime(end_utc)
    tf_dt = datetime(*tf_elts[0:3]) + timedelta(days=1)
    endtime = tf_dt.isoformat('T')
    app.logger.debug(tf_dt)
    

    # query GRQ SOAP service
    app.logger.debug(app.config['GRQ_URL'])
    p = Proxy(app.config['GRQ_URL'])
    res_xml =  p.geoRegionQuery('CloudSat', '2B-GEOPROF.R04', None, starttime,
                                endtime, -180, 180, -90, 90, 'Large')
    root = get_etree(res_xml)
    nsmap = get_nsmap(res_xml)
    cs_dict = { 'count': 0, 'results': {}}
    app.logger.debug(res_xml)
    app.logger.debug(nsmap)
    for res in root.xpath('.//_:result', namespaces=nsmap):
        objectid = str(res.xpath('./_:objectid/text()', namespaces=nsmap)[0])
        d = cs_dict['results'][objectid] = {}
        d['starttime'] = str(res.xpath('./_:starttime/text()', namespaces=nsmap)[0])
        d['endtime'] = eval(res.xpath('./_:endtime/text()', namespaces=nsmap)[0])
        d['lonMin'] = eval(res.xpath('./_:lonMin/text()', namespaces=nsmap)[0])
        d['lonMax'] = eval(res.xpath('./_:lonMax/text()', namespaces=nsmap)[0])
        d['latMin'] = eval(res.xpath('./_:latMin/text()', namespaces=nsmap)[0])
        d['latMax'] = eval(res.xpath('./_:latMax/text()', namespaces=nsmap)[0])
        d['urls'] = [str(i) for i in res.xpath('./_:urls/_:url/text()', namespaces=nsmap)]
    cs_dict['count'] = len(cs_dict['results'])

    return cs_dict 


def coarse_match_cloudsat(a_tinfo, cs_tinfo, time_tol=300.):
    """Return list of CloudSat ids that matchup with the AIRS granule's
       start and end time. Filter out matches that exceed time tolerance."""

    # get CloudSat ids and granule time array
    cs_ids = cs_tinfo['ids']
    cs_granule_times = cs_tinfo['granule_times']
    if cs_granule_times.shape == (0,):
        raise RuntimeError("No CloudSat granules found.")

    # find CloudSat granules that bound AIRS start and end times
    app.logger.debug("a_tinfo: %s" % pformat(a_tinfo))
    ti_idx = np.where(np.logical_and(a_tinfo['start_utc'] >= cs_granule_times[:,0],
                                     a_tinfo['start_utc'] <= cs_granule_times[:,1]))

    tf_idx = np.where(np.logical_and(a_tinfo['end_utc'] >= cs_granule_times[:,0],
                                     a_tinfo['end_utc'] <= cs_granule_times[:,1]))

    # if no match for AIRS start time but there is for end time, use end time's match
    if len(ti_idx[0]) == 0 and len(tf_idx[0]) != 0:
        app.logger.debug("Failed to find CloudSat granule with start/end time " +
                         "bounding AIRS start time %s. Using match from AIRS end time."
                         % a_tinfo['start_utc'])
        ti_idx = tf_idx

    # if no match for AIRS end time but there is for start time, use start time's match
    if len(ti_idx[0]) != 0 and len(tf_idx[0]) == 0:
        app.logger.debug("Failed to find CloudSat granule with start/end time " +
                         "bounding AIRS end time %s. Using match from AIRS start time."
                         % a_tinfo['end_utc'])
        tf_idx = ti_idx

    # if no match for both AIRS start and end times, find closest match
    if len(ti_idx[0]) == 0 and len(tf_idx[0]) == 0:
        # find closest to AIRS start time
        time_diffs_start = np.fabs(a_tinfo['start_utc'] - cs_granule_times)
        closest_to_start = np.unravel_index(time_diffs_start.argmin(), time_diffs_start.shape)
        min_start_diff = time_diffs_start[closest_to_start]
        app.logger.debug("time_diffs_start: %s" % time_diffs_start)
        app.logger.debug("closest_to_start: %s" % str(closest_to_start))
        app.logger.debug("min start time diff: %s" % min_start_diff)

        # find closest to AIRS start time
        time_diffs_end = np.fabs(a_tinfo['end_utc'] - cs_granule_times)
        closest_to_end = np.unravel_index(time_diffs_end.argmin(), time_diffs_end.shape)
        min_end_diff = time_diffs_end[closest_to_end]
        app.logger.debug("time_diffs_end: %s" % time_diffs_end)
        app.logger.debug("closest_to_end: %s" % str(closest_to_end))
        app.logger.debug("min end time diff: %s" % min_end_diff)

        # get the smallest difference
        if min_start_diff < min_end_diff:
            if min_start_diff <= time_tol:
                ti_idx = ([closest_to_start[0]],)
                tf_idx = ([closest_to_start[0]],)
            else:
                app.logger.debug("min start time diff exceeded time " +
                                 "tolerance (%s seconds): %s" % 
                                 (time_tol, min_start_diff))
        elif min_end_diff < min_start_diff:
            if min_end_diff <= time_tol:
                ti_idx = ([closest_to_end[0]],)
                tf_idx = ([closest_to_end[0]],)
            else:
                app.logger.debug("min end time diff exceeded time " +
                                 "tolerance (%s seconds): %s" % 
                                 (time_tol, min_end_diff))

    app.logger.debug("ti_idx: %s" % ti_idx[0])
    app.logger.debug("tf_idx: %s" % tf_idx[0])

    if len(ti_idx[0]) == 0 and len(tf_idx[0]) == 0:
        raise RuntimeError("Failed to find coarse matchup.")

    # add slop granules before and after matched indexes
    matched_idx = range(ti_idx[0][0], tf_idx[0][0]+1)
    if ti_idx[0][0] >= 0: matched_idx.insert(0, ti_idx[0][0]-1)
    if tf_idx[0][0]+1 < len(cs_ids): matched_idx.append(tf_idx[0][0]+1)
    app.logger.debug("matched_idx: %s" % matched_idx)
    matched_ids = np.take(cs_ids, matched_idx).tolist()
    app.logger.debug("matched times: %s" % cs_granule_times[matched_idx])
    app.logger.debug("matched cs_ids: %s" % matched_ids)

    return matched_ids


#@jit('f8[:],f8[:],i4[:,:](f4[:,:],f4[:,:],f4[:,:],f4[:,:,:,:],f4[:,:,:,:],f4[:,:])')
def best_match(lons_cs, lats_cs, profile_utc_cs, lon_airs, lat_airs, profile_utc_airs):
    """Find closest AIRS pixel to CloudSat pixel by distance. Return matchup indices,
       distances, and time differences for these matchups."""

    #app.logger.debug("lons_cs: %s %s" % (str(lons_cs.shape), lons_cs.dtype))
    #app.logger.debug("lats_cs: %s %s" % (str(lats_cs.shape), lats_cs.dtype))
    #app.logger.debug("profile_utc_cs: %s %s" % (str(profile_utc_cs.shape), profile_utc_cs.dtype))
    #app.logger.debug("lon_airs: %s %s" % (str(lon_airs.shape), lon_airs.dtype))
    #app.logger.debug("lat_airs: %s %s" % (str(lat_airs.shape), lat_airs.dtype))
    #app.logger.debug("profile_utc_airs: %s %s" % (str(profile_utc_airs.shape), profile_utc_airs.dtype))

    # loop over CloudSat pixels
    dists = np.zeros(shape=(lats_cs.shape[0],))
    time_diffs = np.zeros(shape=(lats_cs.shape[0],))
    matchup_idx = np.zeros(shape=(lats_cs.shape[0], 4), dtype=np.int)
    for i in range(lats_cs.shape[0]):
        lat_cs = lats_cs[i]
        lon_cs = lons_cs[i]
     
        #calculate diffs
        d_lat = lat_airs - lat_cs
        d_lon = lon_airs - lon_cs

        #calculate distance using great circle
        dist = 2. * RADIUS_EARTH * np.arcsin(
            np.sqrt(
                (np.sin(d_lat * DEG2RAD/2.))**2 + 
                np.cos(lat_airs * DEG2RAD) * 
                np.cos(lat_cs * DEG2RAD) * 
                (np.sin(d_lon * DEG2RAD/2.))**2
            )
        )

        closest_airs_idx = np.unravel_index(dist.argmin(), dist.shape)
        d = dist[closest_airs_idx]
        #app.logger.debug("d: %s %s" % (str(d.shape), str(d)))
        #app.logger.debug("closest_airs_idx: %s %s" % (type(closest_airs_idx), str(closest_airs_idx)))
        dists[i] = d
        time_diffs[i] = np.fabs(profile_utc_airs[closest_airs_idx[0:2]] - profile_utc_cs[i])
        matchup_idx[i,:] = closest_airs_idx

    #app.logger.debug("dists: %s %s" % (str(dists.shape), dists.dtype))
    #app.logger.debug("time_diffs: %s %s" % (str(time_diffs.shape), time_diffs.dtype))
    #app.logger.debug("matchup_idx: %s %s" % (str(matchup_idx.shape), matchup_idx.dtype))
    return dists, time_diffs, matchup_idx


def fine_match_cloudsat(airs_dap_url, a_tinfo, matched_cs_ids, cs_tinfo, cs_minfo, matchup_file, dist_tol=12., time_tol=300.):
    """Perform fine matchup while filtering out any matchups that do not conform to
       the specified distance (in km) and time (in seconds) tolerances. Generate
       NetCDF4 file containing matchup information."""

    #app.logger.debug("airs_dap_url: %s" % airs_dap_url)
    #app.logger.debug("a_tinfo: %s" % pformat(a_tinfo))
    app.logger.debug("matched_cs_ids: %s" % matched_cs_ids)
    app.logger.debug("cs_tinfo['granule_times']: %s" % pformat(cs_tinfo['granule_times']))
    #app.logger.debug("cs_tinfo: %s" % pformat(cs_tinfo))
    #app.logger.debug("cs_minfo: %s" % pformat(cs_minfo))

    # PROV-ES document
    doc = ProvEsDocument(namespaces=ADDITIONAL_NAMESPACES)
    input_ids = []
    output_ids = []

    # PROV-ES values for AIRS input
    airs_platform = AIRS_COLLECTION_INFO['platform']
    airs_platform_title = AIRS_COLLECTION_INFO['platform_title']
    airs_instrument = AIRS_COLLECTION_INFO['instrument']
    airs_instrument_title = AIRS_COLLECTION_INFO['instrument_title']
    airs_sensor = AIRS_COLLECTION_INFO['sensor']
    airs_sensor_title = AIRS_COLLECTION_INFO['sensor_title']
    airs_gov_org = AIRS_COLLECTION_INFO['gov_org']
    airs_gov_org_title = AIRS_COLLECTION_INFO['gov_org_title']
    airs_access_url = AIRS_COLLECTION_INFO['access_url']
    doc.governingOrganization(airs_gov_org, label=airs_gov_org_title)
    doc.platform(airs_platform, [airs_instrument], label=airs_platform_title)
    doc.instrument(airs_instrument, airs_platform, [airs_sensor], [airs_gov_org],
                   label=airs_instrument_title)
    doc.sensor(airs_sensor, airs_instrument, label=airs_sensor_title)

    # PROV-ES values for CloudSat input
    cs_platform = CLOUDSAT_COLLECTION_INFO['platform']
    cs_platform_title = CLOUDSAT_COLLECTION_INFO['platform_title']
    cs_instrument = CLOUDSAT_COLLECTION_INFO['instrument']
    cs_instrument_title = CLOUDSAT_COLLECTION_INFO['instrument_title']
    cs_sensor = CLOUDSAT_COLLECTION_INFO['sensor']
    cs_sensor_title = CLOUDSAT_COLLECTION_INFO['sensor_title']
    cs_gov_org = CLOUDSAT_COLLECTION_INFO['gov_org']
    cs_gov_org_title = CLOUDSAT_COLLECTION_INFO['gov_org_title']
    cs_access_url = CLOUDSAT_COLLECTION_INFO['access_url']
    if cs_gov_org != airs_gov_org:
        doc.governingOrganization(cs_gov_org, label=cs_gov_org_title)
    doc.platform(cs_platform, [cs_instrument], label=cs_platform_title)
    doc.instrument(cs_instrument, cs_platform, [cs_sensor], [cs_gov_org],
                   label=cs_instrument_title)
    doc.sensor(cs_sensor, cs_instrument, label=cs_sensor_title)

    # PROV-ES values for WVCC matchup software
    algorithm = SOFTWARE_INFO['algorithm']
    software_version = SOFTWARE_INFO['software_version']
    software_title = SOFTWARE_INFO['software_title']
    software = SOFTWARE_INFO['software']
    doc.software(software, [algorithm], software_version, label=software_title)

    # PROV-ES values for WVCC matchup index products
    wvcc_level = MATCHUP_INFO['level']
    wvcc_version = MATCHUP_INFO['version']
    wvcc_doi = MATCHUP_INFO['doi']
    wvcc_short_name = MATCHUP_INFO['short_name']
    wvcc_collection = MATCHUP_INFO['collection']
    wvcc_collection_label = MATCHUP_INFO['collection_label']
    wvcc_collection_loc = MATCHUP_INFO['collection_loc']
    doc.collection(wvcc_collection, wvcc_doi, wvcc_short_name, wvcc_collection_label,
                   [wvcc_collection_loc], [airs_instrument, cs_instrument],
                   wvcc_level, wvcc_version, label=wvcc_collection_label)
    wvcc_ds = doc.granule("hysds:%s" % get_uuid(matchup_file), wvcc_doi, 
                          [os.path.abspath(matchup_file)], 
                          [airs_instrument, cs_instrument],
                          wvcc_collection, wvcc_level, wvcc_version,
                          label=os.path.basename(matchup_file))
    output_ids.append(wvcc_ds.identifier)

    # get AIRS info via DAP
    a_ds = open_url(airs_dap_url)

    # open netcdf4 file to store matchup info
    # create dims, variables, and populate attributes
    rootgrp = Dataset(matchup_file, 'w')
    rootgrp.VERSION = app.config['MATCHUP_VERSION']
    rootgrp.AIRS_DAP_URL = airs_dap_url
    rootgrp.AIRS_FILE = os.path.basename(airs_dap_url)
    rootgrp.PRODUCTIONDATE = datetime.utcnow().isoformat('T')
    rootgrp.IDENTIFIER_PRODUCT_DOI = wvcc_doi
    rootgrp.IDENTIFIER_PRODUCT_DOI_AUTHORITY = "http://dx.doi.org/"
    ti_dt = datetime(*time.gmtime(a_tinfo['start_utc'])[0:6])
    startdate, starttime = ti_dt.isoformat('T').split('T')
    rootgrp.RANGEBEGINNINGDATE = startdate
    rootgrp.RANGEBEGINNINGTIME = starttime
    tf_dt = datetime(*time.gmtime(a_tinfo['end_utc'])[0:6])
    enddate, endtime = tf_dt.isoformat('T').split('T')
    rootgrp.RANGEENDINGDATE = enddate
    rootgrp.RANGEENDINGTIME = endtime
    if hasattr(a_ds, 'CoreMetadata'):
        coremetadata = a_ds.CoreMetadata
    elif hasattr(a_ds, 'coremetadata'):
        coremetadata = a_ds.coremetadata
    else:
        raise RuntimeError("Couldn't find attribute CoreMetadata or coremetadata.")
    rootgrp.NORTHBOUNDINGCOORDINATE = coremetadata['INVENTORYMETADATA']['SPATIALDOMAINCONTAINER']['HORIZONTALSPATIALDOMAINCONTAINER']['BOUNDINGRECTANGLE']['NORTHBOUNDINGCOORDINATE']['VALUE']
    rootgrp.SOUTHBOUNDINGCOORDINATE = coremetadata['INVENTORYMETADATA']['SPATIALDOMAINCONTAINER']['HORIZONTALSPATIALDOMAINCONTAINER']['BOUNDINGRECTANGLE']['SOUTHBOUNDINGCOORDINATE']['VALUE']
    rootgrp.EASTBOUNDINGCOORDINATE = coremetadata['INVENTORYMETADATA']['SPATIALDOMAINCONTAINER']['HORIZONTALSPATIALDOMAINCONTAINER']['BOUNDINGRECTANGLE']['EASTBOUNDINGCOORDINATE']['VALUE']
    rootgrp.WESTBOUNDINGCOORDINATE = coremetadata['INVENTORYMETADATA']['SPATIALDOMAINCONTAINER']['HORIZONTALSPATIALDOMAINCONTAINER']['BOUNDINGRECTANGLE']['WESTBOUNDINGCOORDINATE']['VALUE']
    rootgrp.DISTANCE_TOLERANCE = "%f km" % dist_tol
    rootgrp.TIME_TOLERANCE = "%f seconds" % time_tol
    matchup_dim = rootgrp.createDimension('matchup', None)
    airs_idx_dim = rootgrp.createDimension('airs_idx_size', 4)
    airs_matchup_var = rootgrp.createVariable('airs_idx', 'i4', ('matchup', 'airs_idx_size',), zlib=True)
    airs_matchup_var.long_name = "matchup AIRS index"
    cs_matchup_var = rootgrp.createVariable('cloudsat_idx', 'i4', ('matchup',), zlib=True)
    cs_matchup_var.long_name = "matchup CloudSat index"
    cs_file_var = rootgrp.createVariable('cloudsat_file', str, ('matchup',), zlib=True)
    cs_file_var.long_name = "CloudSat file for matchup"
    cs_dap_var = rootgrp.createVariable('cloudsat_dap_url', str, ('matchup',), zlib=True)
    cs_dap_var.long_name = "CloudSat DAP URL for matchup"
    lon_cs_var = rootgrp.createVariable('lon_cs', 'f8', ('matchup',), zlib=True)
    lon_cs_var.long_name = "CloudSat longitude"
    lon_cs_var.description = "longitude for matched up CloudSat footprint"
    lon_cs_var.units = "degrees"
    lat_cs_var = rootgrp.createVariable('lat_cs', 'f8', ('matchup',), zlib=True)
    lat_cs_var.long_name = "CloudSat latitude"
    lat_cs_var.description = "latitude for matched up CloudSat footprint"
    lat_cs_var.units = "degrees"
    time_cs_var = rootgrp.createVariable('time_cs', 'f8', ('matchup',), zlib=True)
    time_cs_var.long_name = "CloudSat profile time"
    time_cs_var.description = "profile UTC time for CloudSat footprint"
    time_cs_var.units = "seconds since Unix epoch (1970-01-01T00:00:00Z)"
    dist_var = rootgrp.createVariable('distance', 'f8', ('matchup',), zlib=True)
    dist_var.long_name = "AIRS-CloudSat matchup pixel distance"
    dist_var.description = "distance between matched up AIRS and CloudSat pixels in kilometers"
    dist_var.units = "km"
    time_diff_var = rootgrp.createVariable('time_diff', 'f8', ('matchup',), zlib=True)
    time_diff_var.long_name = "AIRS-CloudSat matchup pixel time difference"
    time_diff_var.description = "profile time difference between matched up AIRS and CloudSat pixels in seconds"
    time_diff_var.units = "seconds"
    lon_airs_var = rootgrp.createVariable('lon_airs', 'f8', ('matchup',), zlib=True)
    lon_airs_var.long_name = "AIRS longitude"
    lon_airs_var.description = "longitude for matched up AIRS footprint"
    lon_airs_var.units = "degrees"
    lat_airs_var = rootgrp.createVariable('lat_airs', 'f8', ('matchup',), zlib=True)
    lat_airs_var.long_name = "AIRS latitude"
    lat_airs_var.description = "latitude for matched up AIRS footprint"
    lat_airs_var.units = "degrees"
    lon_amsu_var = rootgrp.createVariable('lon_amsu', 'f8', ('matchup',), zlib=True)
    lon_amsu_var.long_name = "AMSU longitude"
    lon_amsu_var.description = "longitude for matched up AMSU footprint"
    lon_amsu_var.units = "degrees"
    lat_amsu_var = rootgrp.createVariable('lat_amsu', 'f8', ('matchup',), zlib=True)
    lat_amsu_var.long_name = "AMSU latitude"
    lat_amsu_var.description = "latitude for matched up AMSU footprint"
    lat_amsu_var.units = "degrees"
    time_amsu_var = rootgrp.createVariable('time_amsu', 'f8', ('matchup',), zlib=True)
    time_amsu_var.long_name = "AMSU profile time"
    time_amsu_var.description = "profile UTC time for AMSU footprint"
    time_amsu_var.units = "seconds since Unix epoch (1970-01-01T00:00:00Z)"

    # get AIRS/AMSU footprint lon/lat and profile times
    lat_airs = get_dap_data(a_ds, ["L2_Standard_atmospheric_surface_product_Data_Fields_latAIRS",
                            "latAIRS"]).astype('f4')
    lon_airs = get_dap_data(a_ds, ["L2_Standard_atmospheric_surface_product_Data_Fields_lonAIRS",
                            "lonAIRS"]).astype('f4')
    lat_amsu = get_dap_data(a_ds, ["L2_Standard_atmospheric_surface_product_Geolocation_Fields_Latitude",
                            "Latitude"]).astype('f4')
    lon_amsu = get_dap_data(a_ds, ["L2_Standard_atmospheric_surface_product_Geolocation_Fields_Longitude",
                            "Longitude"]).astype('f4')
    #app.logger.debug("lat_airs, lat_airs.shape: %s %s" % (lat_airs, lat_airs.shape))
    #app.logger.debug("lon_airs, lon_airs.shape: %s %s" % (lon_airs, lon_airs.shape))

    # track best dist, time diff, matchup_idx
    best = None

    # loop over matched CloudSat granule pixels and match
    cs_dap_url_used = []
    last_matchup_idx = 0
    for cs_id in matched_cs_ids:
        # get Cloudsat profile utc
        cs_file_base = os.path.basename(cs_minfo['results'][cs_id]['dap_urls'][0])
        cs_dap_url = cs_minfo['results'][cs_id]['dap_urls'][0]
        cs_ds = open_url(cs_dap_url)
        prf_time = cs_ds.Profile_time.data[:]
        tai_start = cs_ds.TAI_start.data[:]
        tai = tai_start + TAI
        utc_start = cs_ds.UTC_start.data[:]
        utc = int(tai/86400)*86400 + utc_start
        cs_profile_utc = prf_time + utc
        #app.logger.debug("cs_profile_utc: %s %s" % (str(cs_profile_utc.shape), cs_profile_utc))

        # get CloudSat lat/lon
        lats_cs = cs_ds.Latitude.data[:]
        #app.logger.debug("lats_cs: %s %s" % (str(lats_cs.shape), lats_cs))
        lons_cs = cs_ds.Longitude.data[:]
        #app.logger.debug("lons_cs: %s %s" % (str(lons_cs.shape), lons_cs))

        #dists, time_diffs, matchup_idx = fast_best_match(lons_cs, lats_cs, cs_profile_utc, 
        dists, time_diffs, matchup_idx = best_match(lons_cs, lats_cs, cs_profile_utc, 
                                                    lon_airs, lat_airs, a_tinfo['profile_utc'])
        #app.logger.debug("dists: %s %s\n%s" % (str(dists.shape), dists.dtype, dists))
        #app.logger.debug("time_diffs: %s %s\n%s" % (str(time_diffs.shape), time_diffs.dtype, time_diffs))
        #app.logger.debug("matchup_idx: %s %s\n%s" % (str(matchup_idx.shape), matchup_idx.dtype, matchup_idx))
        app.logger.debug("best distance (km), time diff (sec), and matchup_idx for %s: | %s | %s | %s" % 
                         (airs_dap_url, dists[0], time_diffs[0], matchup_idx[0]))

        # set best match
        if best is None:
            best = {
                'by_dist': {
                    'dist': dists[0],
                    'time_diff': time_diffs[0],
                    'matchup_idx': matchup_idx[0]
                },
                'by_time': {
                    'dist': dists[0],
                    'time_diff': time_diffs[0],
                    'matchup_idx': matchup_idx[0]
                }
            }
        else:
            if dists[0] < best['by_dist']['dist']:
                best['by_dist'] = {
                    'dist': dists[0],
                    'time_diff': time_diffs[0],
                    'matchup_idx': matchup_idx[0]
                }
            if time_diffs[0] < best['by_time']['time_diff']:
                best['by_time'] = {
                    'dist': dists[0],
                    'time_diff': time_diffs[0],
                    'matchup_idx': matchup_idx[0]
                }

        # filter out matchups that exceed the distance and time tolerances
        matched_tols = np.where(np.logical_and(dists <= dist_tol, time_diffs <= time_tol))
        app.logger.debug("matched_tols: %s %s" % (type(matched_tols), matched_tols))

        # skip if no matchups passed
        matched_tols_count = len(matched_tols[0])
        if matched_tols_count == 0:
            app.logger.debug("No matchups found after filtering. Continuing on.")
            continue

        # get filtered data
        filtered_matchup_idx = matchup_idx[matched_tols]
        filtered_dists = dists[matched_tols]
        filtered_time_diffs = time_diffs[matched_tols]
        app.logger.debug("filtered_matchup_idx: %s %s\n%s" % (str(filtered_matchup_idx.shape),
                                                              filtered_matchup_idx.dtype,
                                                              filtered_matchup_idx))

        # append matchup data to variables
        cs_matchup_var[last_matchup_idx:] = matched_tols[0]
        airs_matchup_var[last_matchup_idx:] = filtered_matchup_idx
        for i in range(last_matchup_idx, last_matchup_idx + matched_tols_count):
            cs_file_var[i] = cs_file_base
            cs_dap_var[i] = cs_dap_url
        dist_var[last_matchup_idx:] = filtered_dists
        time_diff_var[last_matchup_idx:] = filtered_time_diffs

        # append CloudSat location and time data
        lon_cs_var[last_matchup_idx:] = lons_cs[matched_tols]
        lat_cs_var[last_matchup_idx:] = lats_cs[matched_tols]
        time_cs_var[last_matchup_idx:] = cs_profile_utc[matched_tols]

        # append AIRS/AMSU location and time data
        airs_idcs = (filtered_matchup_idx[:,0], filtered_matchup_idx[:,1],
                     filtered_matchup_idx[:,2], filtered_matchup_idx[:,3])
        amsu_idcs = (filtered_matchup_idx[:,0], filtered_matchup_idx[:,1])
        lon_airs_var[last_matchup_idx:] = lon_airs[airs_idcs]
        lat_airs_var[last_matchup_idx:] = lat_airs[airs_idcs]
        lon_amsu_var[last_matchup_idx:] = lon_amsu[amsu_idcs]
        lat_amsu_var[last_matchup_idx:] = lat_amsu[amsu_idcs]
        time_amsu_var[last_matchup_idx:] = a_tinfo['profile_utc'][amsu_idcs]

        # save last index used
        last_matchup_idx += matched_tols_count

        # append to list of cs dap urls used
        cs_dap_url_used.append(cs_dap_url)
        
    # close
    rootgrp.close()


    # print out best over match by time and distance
    app.logger.debug("best overall match by distance for %s: | %s | %s | %s" % 
                     (airs_dap_url, best['by_dist']['dist'], best['by_dist']['time_diff'],
                      best['by_dist']['matchup_idx']))
    app.logger.debug("best overall match by time for %s: | %s | %s | %s" % 
                     (airs_dap_url, best['by_time']['dist'], best['by_time']['time_diff'],
                      best['by_time']['matchup_idx']))

    # if no data was added, delete NetCDF4 file and raise error
    if last_matchup_idx == 0:
        if os.path.exists(matchup_file): os.unlink(matchup_file)
        raise RuntimeError("Failed to write matchup indexes that passed time and distance tolerances.") 

    # create PROV-ES for AIRS
    match = AIRS_GRANULE_RE.search(airs_dap_url)
    if not match:
        raise RuntimeError("Failed to match AIRS granule regex: %s" % airs_dap_url)
    a_yy, a_mm, a_dd, a_gran, a_lev, a_prod, a_vers = match.groups() 
    a_doi = AIRS_METADATA_MAP.get(a_prod, {}).get('doi', None)
    a_short_name = AIRS_METADATA_MAP.get(a_prod, {}).get('name', None)
    a_label = AIRS_METADATA_MAP.get(a_prod, {}).get('label', None)
    a_loc = AIRS_METADATA_MAP.get(a_prod, {}).get('location', None)
    if a_loc is None: a_loc = []
    else: a_loc = [a_loc]
    doc.collection(a_doi, a_doi, a_short_name, a_label, a_loc, [airs_instrument],
                   a_lev, a_vers, label=a_label)
    airs_ds = doc.granule('hysds:%s' % get_uuid(airs_dap_url), a_doi,
                          [airs_dap_url], [airs_instrument], a_doi,
                          a_lev, a_vers, label=os.path.basename(airs_dap_url))
    input_ids.append(airs_ds.identifier)

    # create PROV-ES for CloudSat inputs used
    match = CS_GRANULE_RE.search(cs_dap_url)
    if not match:
        raise RuntimeError("Failed to match CloudSat granule regex: %s" % cs_dap_url)
    cs_lev, cs_prod, cs_vers = match.groups() 
    cs_doi = CS_METADATA_MAP.get(cs_prod, {}).get('doi', None)
    cs_short_name = CS_METADATA_MAP.get(cs_prod, {}).get('name', None)
    cs_label = CS_METADATA_MAP.get(cs_prod, {}).get('label', None)
    cs_loc = CS_METADATA_MAP.get(cs_prod, {}).get('location', None)
    if cs_loc is None: cs_loc = []
    else: cs_loc = [cs_loc]
    cs_col_id = "eos:CloudSat-CPR-%s-%s-%s" % (cs_lev, cs_prod, cs_vers)
    doc.collection(cs_col_id, cs_doi, cs_short_name, cs_label, cs_loc,
                   [cs_instrument], cs_lev, cs_vers, label=cs_label)
    for i, cs_dap_url in enumerate(cs_dap_url_used):
        cs_ds = doc.granule('hysds:%s' % get_uuid(cs_dap_url), cs_doi, [cs_dap_url],
                            [cs_instrument], cs_col_id, cs_lev, cs_vers,
                            label=os.path.basename(cs_dap_url))
        input_ids.append(cs_ds.identifier)

    # create PROV-ES for processStep
    fake_time = datetime.utcnow().isoformat() + 'Z'
    rt_ctx_id = "hysds:%s" % get_uuid(
        'distance_tolerance:%s km; time_tolerance:%s secs' % (dist_tol, time_tol))
    doc.runtimeContext(rt_ctx_id, [ 'distance_tolerance:%s km' % dist_tol,
                                    'time_tolerance:%s secs' % time_tol ])
    job_id = "generate_airs_cloudsat_matchups-%s" % fake_time
    doc.processStep('hysds:%s' % get_uuid(job_id), fake_time, 
                    fake_time, [software], None, rt_ctx_id, 
                    input_ids, output_ids, label=job_id)

    # dump PROV-ES
    prod_dir = os.path.dirname(matchup_file)
    prod_id = os.path.basename(prod_dir)
    prov_es_file = os.path.join(prod_dir, "%s.prov_es.json" % prod_id)
    with open(prov_es_file, 'w') as f:
        json.dump(json.loads(doc.serialize()), f, indent=2, sort_keys=True)


def write_matchup_txt(matchup_file, txt_file):
    """Write matchup indices to text file."""

    # get matchup info from nc4 file
    nc = Dataset(matchup_file)
    cs_idcs = nc.variables['cloudsat_idx'][:]
    airs_idcs = nc.variables['airs_idx'][:]
    cs_files = nc.variables['cloudsat_file'][:]
    dists = nc.variables['distance'][:]
    time_diffs = nc.variables['time_diff'][:]

    # group matchups by AIRS and AMSU indexes
    amd = {}
    for i, airs_idc in enumerate(airs_idcs):
        idx = tuple(airs_idc)
        amd.setdefault(idx, {}).setdefault(cs_files[i], []).append(cs_idcs[i])
        amd.setdefault(idx[0:2], {}).setdefault(cs_files[i], []).append(cs_idcs[i])

    # open file
    with open(txt_file, 'w') as f:
        # write headers
        for attr in nc.ncattrs():
            if attr == 'AIRS_DAP_URL': continue
            f.write("#%s=%s\n" % (attr, getattr(nc, attr)))

        # write data
        airs_idcs = [i for i in amd if len(i) == 4]
        airs_idcs.sort()
        amsu_idc_done = {}
        for airs_idc in airs_idcs:
            amsu_idc = airs_idc[0:2]
            if amsu_idc in amsu_idc_done: pass
            else:
                f.write("%s\n" % str(amsu_idc))
                for cs_file in sorted(amd[amsu_idc]):
                    cs_idcs = amd[amsu_idc][cs_file]
                    f.write("%d -- %s %s\n" % (len(cs_idcs), cs_file, cs_idcs))
                    amsu_idc_done[amsu_idc] = True
            f.write("%s\n" % str(airs_idc))
            for cs_file in sorted(amd[airs_idc]):
                cs_idcs = amd[airs_idc][cs_file]
                f.write("%d -- %s %s\n" % (len(cs_idcs), cs_file, cs_idcs))


def get_metadata(nc_file, tags, dataset='WVCC_MATCHUP_INDICES'):
    """Return metadata from matchup file for ingestion into GRQ."""

    # get data
    nc = Dataset(nc_file)
    start_time = "%sT%sZ" % (nc.getncattr('RANGEBEGINNINGDATE'),
                             nc.getncattr('RANGEBEGINNINGTIME'))
    end_time = "%sT%sZ" % (nc.getncattr('RANGEENDINGDATE'),
                           nc.getncattr('RANGEENDINGTIME'))
    north = nc.getncattr('NORTHBOUNDINGCOORDINATE')
    south = nc.getncattr('SOUTHBOUNDINGCOORDINATE')
    west = nc.getncattr('WESTBOUNDINGCOORDINATE')
    east = nc.getncattr('EASTBOUNDINGCOORDINATE')
    version = nc.getncattr('VERSION')
    lon = nc.variables['lon_airs'][:]
    lat = nc.variables['lat_airs'][:]
    coords = [[lon[i], lat[i]] for i in range(len(lon))]

    # return metadata
    return {
        "version": version,
        "level": "L2",
        "tags": tags.split(),
        "data_product_name": dataset,
        "starttime": start_time,
        "center": {
            "type": "point",
            "coordinates": coords[len(coords)/2],
        },
        "bbox": [
            [west, south],
            [west, north],
            [east, north],
            [east, south],
            [west, south],
        ],
        "location": {
            "type": "linestring",
            "coordinates": coords,
        },
        "endtime": end_time,
        "url": []
    }
