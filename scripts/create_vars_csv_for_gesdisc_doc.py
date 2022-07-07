#!/usr/bin/env python
import os, sys
from netCDF4 import Dataset


def walktree(top):
    for k,v in top.groups.iteritems():
        #print("group: %s" % os.path.join(top.path, k))
        for k2,v2 in v.variables.iteritems():
            #print("var: %s" % os.path.join(top.path, k, k2))
            desc = "%s" % v2.__dict__.get('long_name', '')
            if v2.__dict__.get('units', None) is not None:
                desc += " (%s)" % v2.__dict__.get('units', None)
            print("%s|%s" % (os.path.join(top.path, k, k2), desc))
        walktree(v)
   

nc_file = "matched-airs.aqua_cloudsat-v4.0-2006.11.08.225.nc4"
ds = Dataset(nc_file)
walktree(ds)
