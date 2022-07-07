#!/usr/bin/env python
import logging
from pprint import pprint

from measures import app
from measures.lib.cloudsat import get_time_info, grq_airs, coarse_match_airs
from measures.lib.utils import filter_info

logging.basicConfig(level=logging.DEBUG)


cloudsat_dap_url = "http://cvo.hysds.net:8080/opendap/cloudsat/2B-GEOPROF.R04/2006/166/2006166131201_00702_CS_2B-GEOPROF_GRANULE_P_R04_E00.hdf"
dap_filter = "http://msas-dap.jpl.nasa.gov/opendap"
url_prop = "urls"
dap_prop = "dap_urls"


#get CloudSat time info
cs_time_info =  get_time_info(cloudsat_dap_url)

# get matching AIRS info
airs_info = grq_airs(cs_time_info['start_utc'], cs_time_info['end_utc'])

# filter dap urls
filter_info(airs_info, dap_filter, url_prop, dap_prop)
pprint(airs_info)

# coarse matchup
coarse_match_dict = coarse_match_airs(cloudsat_dap_url, cs_time_info, airs_info)
