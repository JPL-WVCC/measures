import os, requests, time, json
from string import Template
from datetime import datetime, timedelta
import dateutil.tz as tz
from urlparse import urlparse
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
from pydap.client import open_url
import numpy as np
from pprint import pformat

from prov_es.model import get_uuid, ProvEsDocument

from measures import app
from .xml import get_etree, get_nsmap
from .constants import (MAJOR_AXIS_RADIUS, MINOR_AXIS_RADIUS,
                        RADIUS_EARTH, DEG2RAD, TAI)
from .prov_info import (CAL_GRANULE_RE, CAL_METADATA_MAP, ADDITIONAL_NAMESPACES,
AIRS_COLLECTION_INFO, CLOUDSAT_COLLECTION_INFO, CALIPSO_COLLECTION_INFO,
SOFTWARE_INFO, MATCHUP_INFO, CAL_MATCHUP_INFO)


np.set_printoptions(precision=12)

# thredds template for CALIPSO on cvo.hysds.net
CALIPSO_THREDDS_TMPL = Template('${calipso_dap_url_base}/${year}/${year}_${month}_${day}/catalog.xml')

# DAP url template
DAP_TMPL = Template('${scheme}://${netloc}${base}${url_path}')

# xpaths
BASE_XPATH = '/thredds:catalog/thredds:service[@name="dap"]/@base'
URL_PATH_XPATH = '/thredds:catalog/thredds:dataset/thredds:dataset/thredds:access/@urlPath'


def get_dap_urls(dap_url_base, time_cs_i, time_cs_f):
    """Return list of CALIPSO DAP urls via THREDDS."""

    urls = []
    while time_cs_i <= time_cs_f:
        thredds_url = CALIPSO_THREDDS_TMPL.substitute(
            calipso_dap_url_base=dap_url_base,
            year="%04d" % time_cs_i.year,
            month="%02d" % time_cs_i.month,
            day="%02d" % time_cs_i.day)
        parsed_url = urlparse(thredds_url)
        time_cs_i += timedelta(days=1)
        r = requests.get(thredds_url)
        r.raise_for_status()
        root = get_etree(r.content)
        nsmap = get_nsmap(r.content)
        base = root.xpath(BASE_XPATH, namespaces=nsmap)[0]
        url_paths = root.xpath(URL_PATH_XPATH, namespaces=nsmap)
        urls.extend([
            DAP_TMPL.substitute(scheme=parsed_url.scheme,
                                netloc=parsed_url.netloc,
                                base=base,
                                url_path=i) for i in url_paths
        ])
    urls.sort()

    return urls


def get_time_info(cal_dap_url):
    """Return dict of time info from the CALIPSO granule."""

    # get start and end date of CALIPSO granule
    ds = open_url(cal_dap_url)
    prf_utc_i = ds.Profile_Time.data[0][0][0] + TAI
    prf_utc_f = ds.Profile_Time.data[-1][0][0] + TAI
    return { 'start_utc': prf_utc_i,
             'end_utc': prf_utc_f }


def get_granule_times(cal_dap_urls):
    """Create array of starttime/endtime UTC values from list of CALIPSO DAP
       urls. Return dict of urls list and granule times."""

    cal_granule_times = []
    profile_time_info = {}
    for cal_dap_url in cal_dap_urls:
        time_info = get_time_info(cal_dap_url)
        profile_time_info[cal_dap_url] = time_info
        cal_granule_times.append([time_info['start_utc'], time_info['end_utc']])
    cal_granule_times = np.array(cal_granule_times)
    app.logger.debug("cal_granule_times: %s %s" % (cal_granule_times, cal_granule_times.shape))
    return { 'dap_urls': cal_dap_urls,
             'granule_times': cal_granule_times,
             'profile_time_info': profile_time_info }


def coarse_match_cloudsat(cs_tinfo, cal_tinfo, time_tol=300.):
    """Return list of CALIPSO urls that matchup with the CloudSat profile time."""

    cal_dap_urls = cal_tinfo['dap_urls']
    cal_granule_times = cal_tinfo['granule_times']

    # find CALIPSO granules that bound CloudSat start and end times
    app.logger.debug("cs_tinfo: %s" % pformat(cs_tinfo))
    ti_idx = np.where(np.logical_and(cs_tinfo['start_utc'] >= cal_granule_times[:,0],
                                     cs_tinfo['start_utc'] <= cal_granule_times[:,1]))

    tf_idx = np.where(np.logical_and(cs_tinfo['end_utc'] >= cal_granule_times[:,0],
                                     cs_tinfo['end_utc'] <= cal_granule_times[:,1]))

    # if no match for CloudSat start time but there is for end time, use end time's match
    if len(ti_idx[0]) == 0 and len(tf_idx[0]) != 0:
        app.logger.debug("Failed to find CALIPSO granule with start/end time " +
                         "bounding CloudSat start time %s. Using match from CloudSat end time."
                         % cs_tinfo['start_utc'])
        ti_idx = tf_idx

    # if no match for CloudSat end time but there is for start time, use start time's match
    if len(ti_idx[0]) != 0 and len(tf_idx[0]) == 0:
        app.logger.debug("Failed to find CALIPSO granule with start/end time " +
                         "bounding CloudSat end time %s. Using match from CloudSat start time."
                         % cs_tinfo['end_utc'])
        tf_idx = ti_idx

    # if no match for both CloudSat start and end times, find closest match
    if len(ti_idx[0]) == 0 and len(tf_idx[0]) == 0:
        # find closest to CloudSat start time
        time_diffs_start = np.fabs(cs_tinfo['start_utc'] - cal_granule_times)
        closest_to_start = np.unravel_index(time_diffs_start.argmin(), time_diffs_start.shape)
        min_start_diff = time_diffs_start[closest_to_start]
        app.logger.debug("time_diffs_start: %s" % time_diffs_start)
        app.logger.debug("closest_to_start: %s" % str(closest_to_start))
        app.logger.debug("min start time diff: %s" % min_start_diff)

        # find closest to AIRS start time
        time_diffs_end = np.fabs(cs_tinfo['end_utc'] - cal_granule_times)
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
    if tf_idx[0][0]+1 < len(cal_dap_urls): matched_idx.append(tf_idx[0][0]+1)
    app.logger.debug("matched_idx: %s" % matched_idx)
    matched_urls = np.take(cal_dap_urls, matched_idx).tolist()
    app.logger.debug("matched times: %s" % cal_granule_times[matched_idx])
    app.logger.debug("matched cal_dap_urls: %s" % matched_urls)

    return matched_urls


def best_match(cal_info, lon_cs, lat_cs, profile_utc_cs):
    """Find closest CALIPSO pixel to CloudSat pixel by distance. Return matchup indices,
       distances, and time differences for these matchups."""

    # extract CALIPSO data
    cal_dap_url = cal_info['dap_url']
    cal_prf_utc = cal_info['profile_utc']
    lats_cal = cal_info['lat']
    lons_cal = cal_info['lon']

    # calculate diffs
    d_lat = lats_cal - lat_cs
    d_lon = lons_cal - lon_cs

    # calculate distance using great circle
    dists = 2. * RADIUS_EARTH * np.arcsin(
        np.sqrt(
            (np.sin(d_lat * DEG2RAD/2.))**2 +
            np.cos(lats_cal * DEG2RAD) *
            np.cos(lat_cs * DEG2RAD) *
            (np.sin(d_lon * DEG2RAD/2.))**2
        )
    )

    #app.logger.debug("dists: %s %s %s" % (str(dists.shape), dists.dtype, dists))
    closest_cal_idx = np.unravel_index(dists.argmin(), dists.shape)
    #app.logger.debug("closest_cal_idx: %s" % closest_cal_idx)
    time_diffs = np.fabs(cal_prf_utc - profile_utc_cs)

    #app.logger.debug("dists: %s %s" % (str(dists.shape), dists.dtype))
    #app.logger.debug("time_diffs: %s %s" % (str(time_diffs.shape), time_diffs.dtype))
    #app.logger.debug("closest_cal_idx: %s" % closest_cal_idx)
    return dists[closest_cal_idx], time_diffs[closest_cal_idx], closest_cal_idx


def fine_match_cloudsat(input_matchup_file, matchup_file, rootgrp, cs_tinfo,
                        matched_cal_urls, cal_tinfo, dist_tol=12., time_tol=300.):
    """Perform fine matchup while filtering out any matchups that do no conform to
       the specified distance (in km) and time (in seconds) tolerances. Append 
       matchup information to the NetCDF4 file."""

    app.logger.debug("matched_cal_urls: %s" % matched_cal_urls)
    #app.logger.debug("cal_tinfo['granule_times']: %s" % pformat(cal_tinfo['granule_times']))

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

    # PROV-ES values for CALIPSO input
    cal_platform = CALIPSO_COLLECTION_INFO['platform']
    cal_platform_title = CALIPSO_COLLECTION_INFO['platform_title']
    cal_instrument = CALIPSO_COLLECTION_INFO['instrument']
    cal_instrument_title = CALIPSO_COLLECTION_INFO['instrument_title']
    cal_sensor = CALIPSO_COLLECTION_INFO['sensor']
    cal_sensor_title = CALIPSO_COLLECTION_INFO['sensor_title']
    cal_gov_org = CALIPSO_COLLECTION_INFO['gov_org']
    cal_gov_org_title = CALIPSO_COLLECTION_INFO['gov_org_title']
    cal_access_url = CALIPSO_COLLECTION_INFO['access_url']
    if cal_gov_org != airs_gov_org:
        doc.governingOrganization(cal_gov_org, label=cal_gov_org_title)
    doc.platform(cal_platform, [cal_instrument], label=cal_platform_title)
    doc.instrument(cal_instrument, cal_platform, [cal_sensor], [cal_gov_org],
                   label=cal_instrument_title)
    doc.sensor(cal_sensor, cal_instrument, label=cal_sensor_title)

    # PROV-ES values for WVCC matchup software
    algorithm = SOFTWARE_INFO['algorithm']
    software_version = SOFTWARE_INFO['software_version']
    software_title = SOFTWARE_INFO['software_title']
    software = SOFTWARE_INFO['software']
    doc.software(software, [algorithm], software_version, label=software_title)

    # PROV-ES for input matchup index file and collection
    doc.collection(MATCHUP_INFO['collection'], MATCHUP_INFO['doi'],
                   MATCHUP_INFO['short_name'], MATCHUP_INFO['collection_label'],
                   [MATCHUP_INFO['collection_loc']], [airs_instrument, cs_instrument],
                   MATCHUP_INFO['level'], MATCHUP_INFO['version'],
                   label=MATCHUP_INFO['collection_label'])
    input_matchup_file_ent = doc.granule("hysds:%s" % get_uuid(input_matchup_file),
                                         MATCHUP_INFO['doi'],
                                         [os.path.abspath(input_matchup_file)],
                                         [airs_instrument, cs_instrument],
                                         MATCHUP_INFO['collection'],
                                         MATCHUP_INFO['level'], MATCHUP_INFO['version'],
                                         label=os.path.basename(input_matchup_file))
    input_ids.append(input_matchup_file_ent.identifier)

    # PROV-ES values for WVCC matchup index products
    wvcc_level = CAL_MATCHUP_INFO['level']
    wvcc_version = CAL_MATCHUP_INFO['version']
    wvcc_doi = CAL_MATCHUP_INFO['doi']
    wvcc_short_name = CAL_MATCHUP_INFO['short_name']
    wvcc_collection = CAL_MATCHUP_INFO['collection']
    wvcc_collection_label = CAL_MATCHUP_INFO['collection_label']
    wvcc_collection_loc = CAL_MATCHUP_INFO['collection_loc']
    doc.collection(wvcc_collection, wvcc_doi, wvcc_short_name, wvcc_collection_label,
                   [wvcc_collection_loc], [airs_instrument, cs_instrument, cal_instrument],
                   wvcc_level, wvcc_version, label=wvcc_collection_label)
    wvcc_ds = doc.granule("hysds:%s" % get_uuid(matchup_file), wvcc_doi,
                          [os.path.abspath(matchup_file)],
                          [airs_instrument, cs_instrument, cal_instrument],
                          wvcc_collection, wvcc_level, wvcc_version,
                          label=os.path.basename(matchup_file))
    output_ids.append(wvcc_ds.identifier)

    # get CloudSat lon/lat and profile times
    cloudsat_idx = rootgrp.variables['cloudsat_idx'][:]
    lat_cs = rootgrp.variables['lat_cs'][:]
    lon_cs = rootgrp.variables['lon_cs'][:]
    time_cs = rootgrp.variables['time_cs'][:]

    # extract CALIPSO data from dap upfront
    matched_cal_info = []
    cal_dap_urls_used = {}
    for cal_dap_url in matched_cal_urls:
        # get CALIPSO profile utc
        app.logger.debug("cal_dap_url: %s" % cal_dap_url)
        ds = open_url(cal_dap_url)
        cal_prf_utc = ds.Profile_Time.data[:] + TAI
        cal_prf_utc = cal_prf_utc.reshape((cal_prf_utc.shape[0]*cal_prf_utc.shape[1]))
        app.logger.debug("cal_prf_utc: %s" % cal_prf_utc)

        # get CALIPSO lat/lon
        lats_cal = ds.Latitude.data[:]
        lats_cal = lats_cal.reshape((lats_cal.shape[0]*lats_cal.shape[1]))
        lons_cal = ds.Longitude.data[:]
        lons_cal = lons_cal.reshape((lons_cal.shape[0]*lons_cal.shape[1]))

        # append to info
        matched_cal_info.append({
            'dap_url': cal_dap_url,
            'profile_utc': cal_prf_utc,
            'lat': lats_cal,
            'lon': lons_cal
        })

    # create CALIPSO variables
    cal_matchup_var = rootgrp.createVariable('calipso_idx', 'i4', ('matchup',),
                                             fill_value=-9999, zlib=True)
    cal_matchup_var.long_name = "matchup CALIPSO index"
    cal_file_var = rootgrp.createVariable('calipso_file', str, ('matchup',),
                                          zlib=True)
    cal_file_var.long_name = "CALIPSO file for matchup"
    cal_dap_var = rootgrp.createVariable('calipso_dap_url', str, ('matchup',),
                                         zlib=True)
    cal_dap_var.long_name = "CALIPSO DAP URL for matchup"
    lon_cal_var = rootgrp.createVariable('lon_cal', 'f8', ('matchup',),
                                         fill_value=-9999., zlib=True)
    lon_cal_var.long_name = "CALIPSO longitude"
    lon_cal_var.description = "longitude for matched up CALIPSO footprint"
    lon_cal_var.units = "degrees"
    lat_cal_var = rootgrp.createVariable('lat_cal', 'f8', ('matchup',),
                                         fill_value=-9999., zlib=True)
    lat_cal_var.long_name = "CALIPSO latitude"
    lat_cal_var.description = "latitude for matched up CALIPSO footprint"
    lat_cal_var.units = "degrees"
    time_cal_var = rootgrp.createVariable('time_cal', 'f8', ('matchup',),
                                          fill_value=-9999., zlib=True)
    time_cal_var.long_name = "CALIPSO profile time"
    time_cal_var.description = "profile UTC time for CALIPSO footprint"
    time_cal_var.units = "seconds since Unix epoch (1970-01-01T00:00:00Z)"
    dist_var = rootgrp.createVariable('distance_cs_cal', 'f8', ('matchup',),
                                      fill_value=-9999., zlib=True)
    dist_var.long_name = "CloudSat-CALIPSO matchup pixel distance"
    dist_var.description = "distance between matched up CloudSat and CALIPSO pixels in kilometers"
    dist_var.units = "km"
    time_diff_var = rootgrp.createVariable('time_diff_cs_cal', 'f8', ('matchup',),
                                           fill_value=-9999., zlib=True)
    time_diff_var.long_name = "CloudSat-CALIPSO matchup pixel time difference"
    time_diff_var.description = "profile time difference between matched up CloudSat and CALIPSO pixels in seconds"
    time_diff_var.units = "seconds"

    # loop over matched CloudSat granule pixels and match
    last_matchup_idx = 0
    for i, cs_idx in enumerate(cloudsat_idx):

        # track best dist, time diff, matchup_idx
        best = None

        for cal_info in matched_cal_info:
            dist, time_diff, matchup_idx = best_match(cal_info,
                                                      lon_cs[i],
                                                      lat_cs[i],
                                                      time_cs[i])

            # filter out matchups that exceed the distance and time tolerances
            if dist > dist_tol:
                #app.logger.debug("dist %s exceeds distance tolerance %s. Skipping." % \
                #                 (dist, dist_tol))
                continue
            if time_diff > time_tol:
                #app.logger.debug("time_diff %s exceeds time tolerance %s. Skipping." % \
                #                 (time_diff, time_tol))
                continue

            # set best match
            if best is None:
                best = {
                    'by_dist': {
                        'dap_url': cal_info['dap_url'],
                        'dist': dist,
                        'time_diff': time_diff,
                        'matchup_idx': matchup_idx,
                        'lon': cal_info['lon'][matchup_idx],
                        'lat': cal_info['lat'][matchup_idx],
                        'profile_utc': cal_info['profile_utc'][matchup_idx]
                    },
                    'by_time': {
                        'dap_url': cal_info['dap_url'],
                        'dist': dist,
                        'time_diff': time_diff,
                        'matchup_idx': matchup_idx,
                        'lon': cal_info['lon'][matchup_idx],
                        'lat': cal_info['lat'][matchup_idx],
                        'profile_utc': cal_info['profile_utc'][matchup_idx]
                    }
                }
            else:
                if dist < best['by_dist']['dist']:
                    best['by_dist'] = {
                        'dap_url': cal_info['dap_url'],
                        'dist': dist,
                        'time_diff': time_diff,
                        'matchup_idx': matchup_idx,
                        'lon': cal_info['lon'][matchup_idx],
                        'lat': cal_info['lat'][matchup_idx],
                        'profile_utc': cal_info['profile_utc'][matchup_idx]
                    }
                if time_diff < best['by_time']['time_diff']:
                    best['by_time'] = {
                        'dap_url': cal_info['dap_url'],
                        'dist': dist,
                        'time_diff': time_diff,
                        'matchup_idx': matchup_idx,
                        'lon': cal_info['lon'][matchup_idx],
                        'lat': cal_info['lat'][matchup_idx],
                        'profile_utc': cal_info['profile_utc'][matchup_idx]
                    }
    
        # set values in variables
        if best is None:
            app.logger.debug("Found no match for CloudSat pixel %s." % cs_idx)
            cal_matchup_var[i] = -9999
            cal_file_var[i] = ""
            cal_dap_var[i] = ""
            lon_cal_var[i] = -9999.
            lat_cal_var[i] = -9999.
            time_cal_var[i] = -9999.
            dist_var[i] = -9999.
            time_diff_var[i] = -9999.
        else:
            app.logger.debug("best distance (km), time diff (sec), and matchup_idx for %s: | %s | %s | %s" %
                             (best['by_time']['dap_url'],
                              best['by_time']['dist'],
                              best['by_time']['time_diff'],
                              best['by_time']['matchup_idx']))
            cal_matchup_var[i] = best['by_time']['matchup_idx']
            cal_file_var[i] = os.path.basename(best['by_time']['dap_url'])
            cal_dap_var[i] = best['by_time']['dap_url']
            lon_cal_var[i] = best['by_time']['lon']
            lat_cal_var[i] = best['by_time']['lat']
            time_cal_var[i] = best['by_time']['profile_utc']
            dist_var[i] = best['by_time']['dist']
            time_diff_var[i] = best['by_time']['time_diff']
            if cal_dap_var[i] not in cal_dap_urls_used:
                cal_dap_urls_used[cal_dap_var[i]] = True

    # create PROV-ES for CALIPSO dap urls
    cal_cols = {}
    for cal_dap_url in cal_dap_urls_used:
        match = CAL_GRANULE_RE.search(cal_dap_url)
        if not match:
            raise RuntimeError("Failed to match CALIPSO granule regex: %s" % cal_dap_url)
        cal_lev, cal_prod, cal_vers = match.groups()
        cal_doi = CAL_METADATA_MAP.get(cal_prod, {}).get('doi', None)
        cal_short_name = CAL_METADATA_MAP.get(cal_prod, {}).get('name', None)
        cal_label = CAL_METADATA_MAP.get(cal_prod, {}).get('label', None)
        cal_loc = CAL_METADATA_MAP.get(cal_prod, {}).get('location', None)
        if cal_loc is None: cal_loc = []
        else: cal_loc = [cal_loc]
        cal_col_id = "eos:CALIPSO-CALIOP-%s-%s-%s" % (cal_lev, cal_prod, cal_vers)
        if cal_col_id not in cal_cols:
            doc.collection(cal_col_id, cal_doi, cal_short_name, cal_label, cal_loc,
                           [cal_instrument], cal_lev, cal_vers, label=cal_label)
            cal_cols[cal_col_id] = True
        cal_ds = doc.granule('hysds:%s' % get_uuid(cal_dap_url), cal_doi,
                          [cal_dap_url], [cal_instrument], cal_col_id,
                          cal_lev, cal_vers, label=os.path.basename(cal_dap_url))
        input_ids.append(cal_ds.identifier)
 
    # create PROV-ES for processStep
    fake_time = datetime.utcnow().isoformat() + 'Z'
    rt_ctx_id = "hysds:%s" % get_uuid(
        'distance_tolerance:%s km; time_tolerance:%s secs' % (dist_tol, time_tol))
    doc.runtimeContext(rt_ctx_id, [ 'distance_tolerance:%s km' % dist_tol,
                                    'time_tolerance:%s secs' % time_tol ])
    job_id = "generate_airs_cloudsat_calipso_matchups-%s" % fake_time
    doc.processStep('hysds:%s' % get_uuid(job_id), fake_time,
                    fake_time, [software], None, rt_ctx_id,
                    input_ids, output_ids, label=job_id)

    # dump PROV-ES
    prod_dir = os.path.dirname(matchup_file)
    prod_id = os.path.basename(prod_dir)
    prov_es_file = os.path.join(prod_dir, "%s.prov_es.json" % prod_id)
    with open(prov_es_file, 'w') as f:
        json.dump(json.loads(doc.serialize()), f, indent=2, sort_keys=True)
