import re
import numpy as np

from .constants import (MAJOR_AXIS_RADIUS, MINOR_AXIS_RADIUS,
                        RADIUS_EARTH, DEG2RAD)


def filter_info(info_dict, regex_str, match_prop, new_prop):
    """Rewrite dataset info dict by matching regex for a property
       and adding matched results to a new property."""

    regex = re.compile(r'%s' % regex_str)
    for k in info_dict['results']:
        for u in info_dict['results'][k][match_prop]:
            if regex.match(u):
                info_dict['results'][k].setdefault(new_prop, []).append(u)


def get_distance(lon1, lat1, lon2, lat2):
    """
    Return distance in kilometers between a point specified by
    lon1/lat1 and another point or array of points specified by lon2/lat2.
    """

    #calculate diffs
    dLat = lat2 - lat1
    dLon = lon2 - lon1

    #calculate distance using great circle
    return 2. * RADIUS_EARTH * np.arcsin(
        np.sqrt(
            (np.sin(d_lat * DEG2RAD/2.))**2 +
            np.cos(lat_airs * DEG2RAD) *
            np.cos(lat_cs * DEG2RAD) *
            (np.sin(d_lon * DEG2RAD/2.))**2
        ) 
    )
