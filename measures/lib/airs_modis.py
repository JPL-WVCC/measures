import os, sys, time, json
from datetime import datetime
from subprocess import check_output, call
from netCDF4 import Dataset
import numpy as np

from prov_es.model import get_uuid, ProvEsDocument

from measures import app
from measures.lib.constants import TAI
from .prov_info import (AIRS_GRANULE_RE, MODIS_AQUA_GRANULE_RE, 
AIRS_METADATA_MAP, MODIS_METADATA_MAP, ADDITIONAL_NAMESPACES, 
AIRS_COLLECTION_INFO, MODIS_AQUA_COLLECTION_INFO, 
SOFTWARE_INFO, MYD_MATCHUP_INFO)


def convert(h4_file, nc4_file):
    """Convert AIRS-MODIS matchup HDF4 files to NetCDF4."""

    # PROV-ES document
    doc = ProvEsDocument(namespaces={'doi': 'https://doi.org/'})
    input_ids = {}
    output_ids = {}

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

    # PROV-ES values for MODIS input
    modis_platform = MODIS_AQUA_COLLECTION_INFO['platform']
    modis_platform_title = MODIS_AQUA_COLLECTION_INFO['platform_title']
    modis_instrument = MODIS_AQUA_COLLECTION_INFO['instrument']
    modis_instrument_title = MODIS_AQUA_COLLECTION_INFO['instrument_title']
    modis_sensor = MODIS_AQUA_COLLECTION_INFO['sensor']
    modis_sensor_title = MODIS_AQUA_COLLECTION_INFO['sensor_title']
    modis_gov_org = MODIS_AQUA_COLLECTION_INFO['gov_org']
    modis_gov_org_title = MODIS_AQUA_COLLECTION_INFO['gov_org_title']
    modis_access_url = MODIS_AQUA_COLLECTION_INFO['access_url']
    if modis_gov_org != airs_gov_org:
        doc.governingOrganization(modis_gov_org, label=modis_gov_org_title)

    # PROV-ES values for AQUA platform;
    # create single platform since both AIRS and MODIS on AQUA
    doc.platform(airs_platform, [airs_instrument, modis_instrument], label=airs_platform_title)

    # PROV-ES values for AIRS instrument & sensor
    doc.instrument(airs_instrument, airs_platform, [airs_sensor], [airs_gov_org],
                   label=airs_instrument_title)
    doc.sensor(airs_sensor, airs_instrument, label=airs_sensor_title)

    # PROV-ES values for MODIS instrument & sensor
    doc.instrument(modis_instrument, modis_platform, [modis_sensor], [modis_gov_org],
                   label=modis_instrument_title)
    doc.sensor(modis_sensor, modis_instrument, label=modis_sensor_title)

    # PROV-ES values for WVCC matchup software
    algorithm = SOFTWARE_INFO['algorithm']
    software_version = SOFTWARE_INFO['software_version']
    software_title = SOFTWARE_INFO['software_title']
    software = SOFTWARE_INFO['software']
    doc.software(software, [algorithm], software_version, label=software_title)

    # check
    if not os.path.exists(h4_file):
        raise(RuntimeError("Cannot find %s.".format(h4_file)))
    output_dir = os.path.dirname(os.path.abspath(nc4_file))
    if not os.path.isdir(output_dir): os.makedirs(output_dir, 0755)

    # add path to h4tonccf_nc4
    path = "%s:%s" % (os.path.join(os.path.dirname(app.root_path), 'scripts'),
                      os.environ['PATH'])

    # convert
    status = call(['h4tonccf_nc4', h4_file, nc4_file],
                  env= { 'HOME': os.environ['HOME'],
                         'PATH': path })
    if status != 0:
        raise(RuntimeError("Got non-zero exit status running h4tonccf: %d" % status))

    # add metadata
    root_grp = Dataset(nc4_file, 'a')
    root_grp.CREATOR = "Mathias Schreier <Mathias.Schreier@jpl.nasa.gov>"
    root_grp.COGNIZANT_ENGINEER = "Gerald Manipon <gmanipon@jpl.nasa.gov>"
    root_grp.VERSION = app.config['AIRS_MODIS_VERSION']
    root_grp.PRODUCTIONDATE = "%sZ" % datetime.utcnow().isoformat('T').split('.')[0]
    root_grp.IDENTIFIER_PRODUCT_DOI = MYD_MATCHUP_INFO['doi']
    root_grp.IDENTIFIER_PRODUCT_DOI_AUTHORITY = "http://dx.doi.org/"

    # append time info
    t = np.ma.masked_equal(root_grp.variables['Time_Point_EV_start_time_'], -9999.)
    ti_dt = datetime(*time.gmtime(t.min() + TAI)[0:6])
    startdate, starttime = ti_dt.isoformat('T').split('T')
    root_grp.RANGEBEGINNINGDATE = startdate
    root_grp.RANGEBEGINNINGTIME = starttime
    tf_dt = datetime(*time.gmtime(t.max() + TAI)[0:6])
    enddate, endtime = tf_dt.isoformat('T').split('T')
    root_grp.RANGEENDINGDATE = enddate
    root_grp.RANGEENDINGTIME = endtime

    # append spatial info
    lat = np.ma.masked_equal(root_grp.variables['Latitude_Point'], -9999.)
    lon = np.ma.masked_equal(root_grp.variables['Longitude_Point'], -9999.)
    root_grp.NORTHBOUNDINGCOORDINATE = lat[0,:].max()
    root_grp.SOUTHBOUNDINGCOORDINATE = lat[-1,:].min()
    root_grp.EASTBOUNDINGCOORDINATE = lon[:,-1].max()
    root_grp.WESTBOUNDINGCOORDINATE = lon[:,0].min()

    # create PROV-ES for MODIS inputs
    modis_collections = {}
    for i in range(root_grp.Comp_FileNumberA):
        modis_file = getattr(root_grp, 'Comp_FileA%d' % i)
        match = MODIS_AQUA_GRANULE_RE.search(modis_file)
        if not match:
            raise RuntimeError("Failed to match MODIS-Aqua granule regex: %s" % modis_file)
        m_prod, m_yy, m_doy, m_time, m_vers = match.groups()
        m_doi = MODIS_METADATA_MAP.get(m_prod, {}).get('doi', None)
        m_short_name = MODIS_METADATA_MAP.get(m_prod, {}).get('name', None)
        m_label = MODIS_METADATA_MAP.get(m_prod, {}).get('label', None)
        m_loc = MODIS_METADATA_MAP.get(m_prod, {}).get('location', None)
        m_lev = MODIS_METADATA_MAP.get(m_prod, {}).get('level', None)
        if m_loc is None: m_loc = []
        else: m_loc = [m_loc]
        if m_doi not in modis_collections:
            m_col = doc.collection(m_doi, m_doi, m_short_name, m_label, m_loc,
                                   [modis_instrument], m_lev, m_vers, label=m_label)
            modis_collections[m_doi] = True
        modis_ds = doc.granule('hysds:%s' % get_uuid(modis_file), m_doi,
                              [modis_file], [modis_instrument], m_doi,
                              m_lev, m_vers, label=os.path.basename(modis_file))
        input_ids[modis_ds.identifier] = True

    # create PROV-ES for AIRS inputs
    airs_collections = {}
    for i in range(root_grp.Comp_FileNumberB):
        airs_file = getattr(root_grp, 'Comp_FileB%d' % i)
        match = AIRS_GRANULE_RE.search(airs_file)
        if not match:
            raise RuntimeError("Failed to match AIRS granule regex: %s" % airs_file)
        a_yy, a_mm, a_dd, a_gran, a_lev, a_prod, a_vers = match.groups()
        a_doi = AIRS_METADATA_MAP.get(a_prod, {}).get('doi', None)
        a_short_name = AIRS_METADATA_MAP.get(a_prod, {}).get('name', None)
        a_label = AIRS_METADATA_MAP.get(a_prod, {}).get('label', None)
        a_loc = AIRS_METADATA_MAP.get(a_prod, {}).get('location', None)
        if a_loc is None: a_loc = []
        else: a_loc = [a_loc]
        if a_doi not in airs_collections:
            a_col = doc.collection(a_doi, a_doi, a_short_name, a_label, a_loc,
                                   [airs_instrument], a_lev, a_vers, label=a_label)
            airs_collections[a_doi] = True
        airs_ds = doc.granule('hysds:%s' % get_uuid(airs_file), a_doi,
                              [airs_file], [airs_instrument], a_doi,
                              a_lev, a_vers, label=os.path.basename(airs_file))
        input_ids[airs_ds.identifier] = True

    # close file
    root_grp.close()

    # PROV-ES for output matchup index file and collection
    col = doc.collection(MYD_MATCHUP_INFO['doi'], MYD_MATCHUP_INFO['doi'],
                         MYD_MATCHUP_INFO['short_name'], MYD_MATCHUP_INFO['collection_label'],
                         [MYD_MATCHUP_INFO['collection_loc']], [airs_instrument, modis_instrument],
                         MYD_MATCHUP_INFO['level'], MYD_MATCHUP_INFO['version'],
                         label=MYD_MATCHUP_INFO['collection_label'])
    matchup_file_ent = doc.granule("hysds:%s" % get_uuid(nc4_file),
                                   MYD_MATCHUP_INFO['doi'], [os.path.abspath(nc4_file)],
                                   [airs_instrument, modis_instrument],
                                   MYD_MATCHUP_INFO['doi'],
                                   MYD_MATCHUP_INFO['level'], MYD_MATCHUP_INFO['version'],
                                   label=os.path.basename(nc4_file))
    output_ids[matchup_file_ent.identifier] = True

    # create PROV-ES for processStep
    fake_time = datetime.utcnow().isoformat() + 'Z'
    job_id = "generate_airs_modis_matchups-%s" % fake_time
    doc.processStep('hysds:%s' % get_uuid(job_id), fake_time,
                    fake_time, [software], None, None,
                    input_ids.keys(), output_ids.keys(), label=job_id)

    # dump PROV-ES
    prod_dir = os.path.dirname(nc4_file)
    prod_id = os.path.basename(prod_dir)
    prov_es_file = os.path.join(prod_dir, "%s.prov_es.json" % prod_id)
    with open(prov_es_file, 'w') as f:
        json.dump(json.loads(doc.serialize()), f, indent=2, sort_keys=True)


def get_metadata(nc_file, tags, dataset='WVCC_AIRS_MDS_IND'):
    """Return metadata from matchup file for ingestion into GRQ."""

    # get data
    nc = Dataset(nc_file)
    start_time = "%sT%sZ" % (nc.getncattr('RANGEBEGINNINGDATE'),
                             nc.getncattr('RANGEBEGINNINGTIME'))
    end_time = "%sT%sZ" % (nc.getncattr('RANGEENDINGDATE'),
                           nc.getncattr('RANGEENDINGTIME'))
    north = nc.getncattr('NORTHBOUNDINGCOORDINATE').astype(int)
    south = nc.getncattr('SOUTHBOUNDINGCOORDINATE').astype(int)
    west = nc.getncattr('WESTBOUNDINGCOORDINATE').astype(int)
    east = nc.getncattr('EASTBOUNDINGCOORDINATE').astype(int)
    version = nc.getncattr('VERSION')
    lon = np.ma.masked_equal(nc.variables['Longitude_Point'][:].flatten().astype(int), -9999).compressed()
    lat = np.ma.masked_equal(nc.variables['Latitude_Point'][:].flatten().astype(int), -9999).compressed()
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
            "type": "polygon",
            "coordinates": [
                #[
                #    [west, south],
                #    [west, north],
                #    [east, north],
                #    [east, south],
                #    [west, south],
                #],
                [
                    [nc.variables['Longitude_Point'][0, 0], nc.variables['Latitude_Point'][0, 0]],
                    [nc.variables['Longitude_Point'][0, 89], nc.variables['Latitude_Point'][0, 89]],
                    [nc.variables['Longitude_Point'][674, 89], nc.variables['Latitude_Point'][674, 89]],
                    [nc.variables['Longitude_Point'][674, 0], nc.variables['Latitude_Point'][674, 0]],
                    [nc.variables['Longitude_Point'][0, 0], nc.variables['Latitude_Point'][0, 0]],
                ],
            ],
        },
        "endtime": end_time,
        "url": []
    }
