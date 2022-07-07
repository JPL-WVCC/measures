import numpy as np
from pprint import pformat

from measures import app
from .constants import (MAJOR_AXIS_RADIUS, MINOR_AXIS_RADIUS,
                        RADIUS_EARTH, DEG2RAD, TAI)

cimport cython
cimport numpy as np


DTYPE_f8 = np.float64
ctypedef np.float64_t DTYPE_f8_t
DTYPE_i4 = np.int32
ctypedef np.int32_t DTYPE_i4_t
DTYPE_f4 = np.float32
ctypedef np.float32_t DTYPE_f4_t


@cython.boundscheck(False)
@cython.wraparound(False)
def best_match(np.ndarray[DTYPE_f4_t, ndim=2] lons_cs,
               np.ndarray[DTYPE_f4_t, ndim=2] lats_cs,
               np.ndarray[DTYPE_f8_t, ndim=2] profile_utc_cs,
               np.ndarray[DTYPE_f4_t, ndim=4] lon_airs,
               np.ndarray[DTYPE_f4_t, ndim=4] lat_airs,
               np.ndarray[DTYPE_f8_t, ndim=2] profile_utc_airs):
    """Find closest AIRS pixel to CloudSat pixel by distance. Return matchup indices,
       distances, and time differences for these matchups."""

    assert lons_cs.dtype == DTYPE_f4
    assert lats_cs.dtype == DTYPE_f4
    assert profile_utc_cs.dtype == DTYPE_f8
    assert lon_airs.dtype == DTYPE_f4
    assert lat_airs.dtype == DTYPE_f4
    assert profile_utc_airs.dtype == DTYPE_f8

    #app.logger.debug("lons_cs: %s %s" % (str(lons_cs.shape), lons_cs.dtype))
    #app.logger.debug("lats_cs: %s %s" % (str(lats_cs.shape), lats_cs.dtype))
    #app.logger.debug("profile_utc_cs: %s %s" % (str(profile_utc_cs.shape), profile_utc_cs.dtype))
    #app.logger.debug("lon_airs: %s %s" % (str(lon_airs.shape), lon_airs.dtype))
    #app.logger.debug("lat_airs: %s %s" % (str(lat_airs.shape), lat_airs.dtype))
    #app.logger.debug("profile_utc_airs: %s %s" % (str(profile_utc_airs.shape), profile_utc_airs.dtype))

    # type indexes
    cdef int rec_len = lats_cs.shape[0]

    # loop over CloudSat pixels
    cdef np.ndarray[DTYPE_f4_t, ndim=1] dists = np.zeros(shape=(rec_len,), dtype=DTYPE_f4)
    cdef np.ndarray[DTYPE_f4_t, ndim=1] time_diffs = np.zeros(shape=(rec_len,), dtype=DTYPE_f4)
    cdef np.ndarray[DTYPE_i4_t, ndim=2] matchup_idx = np.zeros(shape=(rec_len, 4), dtype=DTYPE_i4)
    cdef int i, shape_1, shape_2, shape_3, shape_4
    cdef DTYPE_f4_t lat_cs, lon_cs, d
    cdef np.ndarray[DTYPE_f4_t, ndim=4] d_lat, d_lon, dist
    for i in range(rec_len):
        lat_cs = lats_cs[i, 0]
        lon_cs = lons_cs[i, 0]
     
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
        shape_0 = dist.shape[0]
        shape_1 = dist.shape[1]
        shape_2 = dist.shape[2]
        shape_3 = dist.shape[3]

        closest_airs_idx = np.unravel_index(dist.argmin(), (shape_0, shape_1, shape_2, shape_3,))
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
