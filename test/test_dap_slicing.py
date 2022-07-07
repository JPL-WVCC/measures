#!/usr/bin/env python
import os, sys, logging
from pprint import pprint
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
import pydap.lib
from pydap.client import open_url


#pydap.lib.CACHE = "/data/work/tmp/pydap_cache/"

logging.basicConfig(level=logging.DEBUG)

airs_dap_url = "http://airspar1u.ecs.nasa.gov/opendap/Aqua_AIRS_Level2/AIRX2RET.006/2007/001/AIRS.2007.01.01.240.L2.RetStd.v6.0.7.0.G13115201512.hdf"


slice_url = "%s?Time[0][0],Latitude[44][29]" % airs_dap_url
ds = open_url(slice_url)
print ds['Time'].data[:].shape
