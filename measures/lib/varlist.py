import os, sys, time, json, requests
from pprint import pformat
from datetime import datetime, timedelta

from measures import app


def create_cfg(cs_geoprof_vars, cs_cldclass_vars, cs_geoprof_lidar_vars,
               airs_retstd_vars, airs_retsup_vars, airs_rad_vars, out_file):
    """Create filtered varlist config file."""

    varlist_cfg = []

    # create cloudsat config
    cs_cfg = { 'instrument': 'CloudSat', 'datasets': [] }
    cs_cfg['datasets'].append({ 'dataset': '2B-GEOPROF', 'variables': cs_geoprof_vars })
    cs_cfg['datasets'].append({ 'dataset': '2B-CLDCLASS', 'variables': cs_cldclass_vars })
    cs_cfg['datasets'].append({ 'dataset': '2B-GEOPROF-LIDAR', 'variables': cs_geoprof_lidar_vars })
    varlist_cfg.append(cs_cfg)

    # create airs config
    airs_cfg = { 'instrument': 'AIRS', 'datasets': [] }
    airs_cfg['datasets'].append({ 'dataset': 'L2_Standard_atmospheric&surface_product', 'variables': airs_retstd_vars })
    airs_cfg['datasets'].append({ 'dataset': 'L2_Support_atmospheric&surface_product', 'variables': airs_retsup_vars })
    airs_cfg['datasets'].append({ 'dataset': 'L1B_AIRS_Science', 'variables': airs_rad_vars })
    varlist_cfg.append(airs_cfg)

    # write file
    with open(out_file, 'w') as f:
        json.dump(varlist_cfg, f, indent=2)

    return out_file
