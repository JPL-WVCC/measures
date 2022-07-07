#!/usr/bin/env python
import os, sys, logging
from pprint import pprint
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
import pydap.lib
from pydap.client import open_url
import cPickle as pickle

from measures import app
from measures.lib import airs as measures_airs
from measures.lib import cloudsat as measures_cs
from measures.lib.utils import filter_info

pydap.lib.CACHE = "/data/work/tmp/pydap_cache/"

logging.basicConfig(level=logging.DEBUG)


# 1 CloudSat file matched
#airs_dap_url = "http://msas-dap.jpl.nasa.gov/opendap/repository/products/airs.aqua/v6/2009/08/08/airx2ret/AIRS.2009.08.08.001.L2.RetStd.v6.0.7.0.G13088193456.hdf"
# 2 CloudSat files matched in old
airs_dap_url = "http://msas-dap.jpl.nasa.gov/opendap/hyrax/repository/products/airs.aqua/v6/2009/08/08/airx2ret/AIRS.2009.08.08.002.L2.RetStd.v6.0.7.0.G13088193546.hdf"
#airs_dap_url = "http://msas-dap.jpl.nasa.gov/opendap/hyrax/repository/products/airs.aqua/v5/2009/08/08/airx2ret/AIRS.2009.08.08.002.L2.RetStd.v5.2.2.0.G09221002717.hdf"
# 2 CloudSat files matched in new
#airs_dap_url = "http://msas-dap.jpl.nasa.gov/opendap/hyrax/repository/products/airs.aqua/v6/2009/08/08/airx2ret/AIRS.2009.08.08.003.L2.RetStd.v6.0.7.0.G13088193743.hdf"

# time tolerance in seconds
time_tol = 300.

# distance tolerance in km
dist_tol = 12.

dap_filter = "^http://cvo.hysds.net:8080/opendap/.*\.hdf$"
url_prop = "urls"
dap_prop = "dap_urls"


# get AIRS time info
a_tinfo_pkl = "a_tinfo.pkl"
if not os.path.exists(a_tinfo_pkl):
    a_tinfo = measures_airs.get_time_info(airs_dap_url)
    with open(a_tinfo_pkl, 'wb') as f:
        pickle.dump(a_tinfo, f)
else:
    with open(a_tinfo_pkl, 'rb') as f:
        a_tinfo = pickle.load(f)
#pprint(a_tinfo)

# get matching CloudSat granules
cs_minfo_pkl = "cs_minfo.pkl"
if not os.path.exists(cs_minfo_pkl):
    cs_minfo = measures_airs.grq_cloudsat(a_tinfo['start_utc'], a_tinfo['end_utc'])

    # filter dap urls
    filter_info(cs_minfo, dap_filter, url_prop, dap_prop)
    #pprint(cs_minfo)

    with open(cs_minfo_pkl, 'wb') as f:
        pickle.dump(cs_minfo, f)
else:
    with open(cs_minfo_pkl, 'rb') as f:
        cs_minfo = pickle.load(f)
#pprint(cs_minfo)

# get cloudsat granule time array
cs_tinfo_pkl = "cs_tinfo.pkl"
if not os.path.exists(cs_tinfo_pkl):
    cs_tinfo = measures_cs.get_granule_times(cs_minfo)

    with open(cs_tinfo_pkl, 'wb') as f:
        pickle.dump(cs_tinfo, f)
else:
    with open(cs_tinfo_pkl, 'rb') as f:
        cs_tinfo = pickle.load(f)
#pprint(cs_tinfo)

# coarse matchup
matched_cs_ids = measures_airs.coarse_match_cloudsat(a_tinfo, cs_tinfo, time_tol)

# fine matchup
matchup_file = "index-airs.aqua_cloudsat-v%s-%s.nc4" % (app.config['MATCHUP_VERSION'],
                                                        os.path.basename(airs_dap_url)[5:19])
measures_airs.fine_match_cloudsat(airs_dap_url, a_tinfo, matched_cs_ids,
                                  cs_tinfo, cs_minfo, matchup_file, 
                                  dist_tol, time_tol)


# create matchup text file
matchup_txt_file = "index-airs.aqua_cloudsat-v%s-%s.txt" % (app.config['MATCHUP_VERSION'],
                                                            os.path.basename(airs_dap_url)[5:19])
measures_airs.write_matchup_txt(matchup_file, matchup_txt_file)
