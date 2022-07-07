import time
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
from pydap.client import open_url
import numpy as np
from pprint import pformat
from datetime import datetime, timedelta
from SOAPpy.WSDL import Proxy


from measures import app
from .constants import TAI
from .xml import get_etree, get_nsmap


def get_time_info(cs_dap_url):
    """Return dict  of time info from the CloudSat granule."""

    # get start and end date of CloudSat granule
    ds = open_url(cs_dap_url)
    prf_time_i = ds.Profile_time.data[0][0]
    prf_time_f = ds.Profile_time.data[-1][0]
    app.logger.debug("Initial and final prf_time: %s %s" % (prf_time_i, prf_time_f))
    tai_start_i = ds.TAI_start.data[0][0]
    tai_start_f = ds.TAI_start.data[-1][0]
    app.logger.debug("Initial and final tai_start: %s %s" % (tai_start_i, tai_start_f))
    tai_i = tai_start_i + TAI
    tai_f = tai_start_f + TAI
    app.logger.debug("Initial and final tai: %s %s" % (tai_i, tai_f))
    utc_start_i = ds.UTC_start.data[0][0]
    utc_start_f = ds.UTC_start.data[-1][0]
    app.logger.debug("Initial and final utc_start: %s %s" % (utc_start_i, utc_start_f))
    utc_i = int(tai_i/86400)*86400 + utc_start_i
    utc_f = int(tai_f/86400)*86400 + utc_start_f
    app.logger.debug("Initial and final utc: %s %s" % (utc_i, utc_f))
    profile_utc_i = prf_time_i + utc_i
    profile_utc_f = prf_time_f + utc_f
    app.logger.debug("Initial and final profile_utc: %s %s" % (profile_utc_i, profile_utc_f))

    return { 'start_utc': profile_utc_i,
             'end_utc': profile_utc_f }


def grq_airs(start_utc, end_utc):
    """Return list of AIRS DAP URLs that match to CloudSat temporally 
       (with +/- 1 day slop)."""

    # get ISO format for times with 1 day slop
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
    res_xml =  p.geoRegionQuery('AIRS', 'RetStd', 'v6', starttime,
                                endtime, -180, 180, -90, 90, 'Large')
    root = get_etree(res_xml)
    nsmap = get_nsmap(res_xml)
    airs_dict = { 'count': 0, 'results': {}}
    app.logger.debug(res_xml)
    app.logger.debug(nsmap)
    for res in root.xpath('.//_:result', namespaces=nsmap):
        objectid = str(res.xpath('./_:objectid/text()', namespaces=nsmap)[0])
        d = airs_dict['results'][objectid] = {}
        d['starttime'] = str(res.xpath('./_:starttime/text()', namespaces=nsmap)[0])
        d['endtime'] = str(res.xpath('./_:endtime/text()', namespaces=nsmap)[0])
        d['lonMin'] = eval(res.xpath('./_:lonMin/text()', namespaces=nsmap)[0])
        d['lonMax'] = eval(res.xpath('./_:lonMax/text()', namespaces=nsmap)[0])
        d['latMin'] = eval(res.xpath('./_:latMin/text()', namespaces=nsmap)[0])
        d['latMax'] = eval(res.xpath('./_:latMax/text()', namespaces=nsmap)[0])
        d['urls'] = [str(i) for i in res.xpath('./_:urls/_:url/text()', namespaces=nsmap)]
    airs_dict['count'] = len(airs_dict['results'])

    return airs_dict 


def get_granule_times(cs_minfo):
    """Create array of starttime/endtime UTC values from CloudSat matchup info.
       Return tuple of CloudSat ids list and the starttime/endtime array."""

    cs_granule_times = []
    profile_time_info = {}
    cs_ids = sorted(cs_minfo['results'])
    for cs_id in cs_ids:
        info = cs_minfo['results'][cs_id]
        if len(info['dap_urls']) == 0:
            raise RuntimeError("Couldn't find DAP url for %s." % cs_id)
        time_info = get_time_info(info['dap_urls'][0])
        profile_time_info[cs_id] = time_info
        cs_granule_times.append([time_info['start_utc'], time_info['end_utc']])
    cs_granule_times = np.array(cs_granule_times)
    app.logger.debug("cs_granule_times: %s %s" % (cs_granule_times, cs_granule_times.shape))
    return { 'ids': cs_ids,
             'granule_times': cs_granule_times,
             'profile_time_info': profile_time_info } 


#def coarse_match_airs(cs_dap_url, cs_time_info, airs_info):
#    """Matchup CloudSat pixels to AIRS pixels in 2 steps:
#    
#    1) coarse matchup a CloudSat pixel to AIRS start and end time
#        a) first look for AIRS granule that bounds the CloudSat time
#        b) if no AIRS granule bounds the CloudSat time, search for
#           closest one
#    2) get closest AIRS pixel by time within the matching AIRS file
#    
#    Return text file with all matchups.
#    """
#
#    # get airs granule start and endtime array    
#    airs_granule_times = []
#    airs_ids = sorted(airs_info['results'])
#    for airs_id in airs_ids:
#        info = airs_info['results'][airs_id]
#        if len(info['dap_urls']) == 0:
#            raise RuntimeError("Couldn't find DAP url for %s." % airs_id)
#        time_info = measures.lib.airs.get_time_info(info['dap_urls'][0])
#        airs_granule_times.append([time_info['start_utc'], time_info['end_utc']])
#    airs_granule_times = np.array(airs_granule_times)
#    #print airs_granule_times
