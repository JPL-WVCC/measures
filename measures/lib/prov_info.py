import re

import measures
from measures import app


AIRS_GRANULE_RE = re.compile(r'AIRS\.(\d{4})\.(\d{2})\.(\d{2})\.(\d{3})\.(.*?)\.(.*?)\.(v.*?)\..*')
CS_GRANULE_RE = re.compile(r'/\d+?_\d+?_CS_(.*?)-(.*?)_GRANULE_P.*?_(R\d+?)_.*')
CAL_GRANULE_RE = re.compile(r'/CAL_LID_(L\d)_(.*?)-.*?-(V\d-\d+)\..*hdf')
MODIS_AQUA_GRANULE_RE = re.compile(r'(MYD\w+?)\.A(\d{4})(\d{3})\.(\d{4})\.(\d{3})\..*')

AIRS_METADATA_MAP = {
    'RetStd': {
        'name': 'AIRX2RET',
        'label': 'Aqua AIRS Level 2 Standard Physical Retrieval (AIRS+AMSU)',
        'doi': 'doi:10.5067/AQUA/AIRS/DATA201',
        'location': 'http://disc.gsfc.nasa.gov/datacollection/AIRX2RET_V006.html',
    },
    'RetSup': {
        'name': 'AIRX2SUP',
        'label': 'Aqua AIRS Level 2 Support Retrieval (AIRS+AMSU)',
        'doi': 'doi:10.5067/AQUA/AIRS/DATA207',
        'location': 'http://disc.gsfc.nasa.gov/datacollection/AIRX2SUP_V006.html',
    },
    'AIRS_Rad': {
        'name': 'AIRIBRAD',
        'label': 'AIRS/Aqua Level 1B Infrared (IR) geolocated and calibrated radiances',
        'doi': 'eos:AQUA-AIRS-L1B-AIRIBRAD',
        'location': 'http://disc.sci.gsfc.nasa.gov/datacollection/AIRIBRAD_V005.html',
    },
}


CS_METADATA_MAP = {
    'GEOPROF': {
        'name': '2B-GEOPROF',
        'label': 'CloudSat CPR 2B-GEOPROF',
        'doi': None,
        'location': 'http://www.cloudsat.cira.colostate.edu/data-products/level-2b/2b-geoprof',
    },
    'PRECIP-COLUMN': {
        'name': '2C-PRECIP-COLUMN',
        'label': 'CloudSat CPR 2C-PRECIP-COLUMN',
        'doi': None,
        'location': 'http://www.cloudsat.cira.colostate.edu/data-products/level-2c/2c-precip-column',
    },
    'CLDCLASS': {
        'name': '2B-CLDCLASS',
        'label': 'CloudSat CPR 2B-CLDCLASS',
        'doi': None,
        'location': 'http://www.cloudsat.cira.colostate.edu/data-products/level-2b/2b-cldclass',
    },
    'CWC-RO': {
        'name': '2B-CWC-RO',
        'label': 'CloudSat CPR 2B-CWC-RO',
        'doi': None,
        'location': 'http://www.cloudsat.cira.colostate.edu/data-products/level-2b/2b-cwc-ro',
    },
    'GEOPROF-LIDAR': {
        'name': '2B-GEOPROF-LIDAR',
        'label': 'CloudSat CPR 2B-GEOPROF-LIDAR',
        'doi': None,
        'location': 'http://www.cloudsat.cira.colostate.edu/data-products/level-2b/2b-geoprof-lidar',
    },
    'TAU': {
        'name': '2B-TAU',
        'label': 'CloudSat CPR 2B-TAU',
        'doi': None,
        'location': 'http://www.cloudsat.cira.colostate.edu/data-products/level-2b/2b-tau',
    },
}


CAL_METADATA_MAP = {
    '333mCLay': {
        'name': 'CAL_LID_L2_333mCLay-ValStage1',
        'label': 'CALIPSO Level 2 Aerosol and Cloud Measurements',
        'doi': None,
        'location': 'https://eosweb.larc.nasa.gov/project/calipso/cal_lid_l2_333mclay-valstage1-v3-30_table',
    },
}


MODIS_METADATA_MAP = {
    'MYD03': {
        'name': 'MYD03',
        'label': 'MODIS/Aqua Geolocation Fields 5-Min L1A Swath 1km',
        'doi': 'doi:10.5067/MODIS/MYD03.006',
        'location': 'http://modaps.nascom.nasa.gov/services/about/products/c6/MYD03.html',
        'level': "L1",
    },
}


ADDITIONAL_NAMESPACES = {
    'doi': 'https://doi.org/',
    'wvcc': 'http://disc.sci.gsfc.nasa.gov/daac-bin/DataHoldingsMEASURES.pl?PROGRAM_List=EricFetzer#',
}


AIRS_COLLECTION_INFO = {
    'platform': "eos:AQUA",
    'platform_title': "AQUA",
    'instrument': "eos:AQUA-AIRS",
    'instrument_title': "AQUA-AIRS",
    'sensor': "eos:AIRS",
    'sensor_title': "Atmospheric Infrared Sounder (AIRS)",
    'gov_org': "eos:NASA",
    'gov_org_title': "National Aeronautics and Space Administration",
    'access_url': "https://airs.jpl.nasa.gov/",
}


CLOUDSAT_COLLECTION_INFO = {
    'platform': "eos:CloudSat",
    'platform_title': "CloudSat",
    'instrument': "eos:CloudSat-CPR",
    'instrument_title': "CloudSat-CPR",
    'sensor': "eos:CPR",
    'sensor_title': "Cloud Profiling Radar (CPR)",
    'gov_org': "eos:NASA",
    'gov_org_title': "National Aeronautics and Space Administration",
    'access_url': "http://cloudsat.atmos.colostate.edu/",
}


CALIPSO_COLLECTION_INFO = {
    'platform': "eos:CALIPSO",
    'platform_title': "Cloud-Aerosol Lidar and Infrared Pathfinder Satellite Observation",
    'instrument': "eos:CALIPSO-CALIOP",
    'instrument_title': "CALIPSO-CALIOP",
    'sensor': "eos:CALIOP",
    'sensor_title': "Cloud-Aerosol LIdar with Orthogonal Polarization (CALIOP)",
    'gov_org': "eos:NASA",
    'gov_org_title': "National Aeronautics and Space Administration",
    'access_url': "https://eosweb.larc.nasa.gov/project/calipso/calipso_table",
}


MODIS_AQUA_COLLECTION_INFO = {
    'platform': "eos:AQUA",
    'platform_title': "AQUA",
    'instrument': "eos:AQUA-MODIS",
    'instrument_title': "AQUA-MODIS",
    'sensor': "eos:MODIS",
    'sensor_title': "Moderate Resolution Imaging Spectroradiometer (MODIS)",
    'gov_org': "eos:NASA",
    'gov_org_title': "National Aeronautics and Space Administration",
    'access_url': "http://modis.gsfc.nasa.gov/",
}


SOFTWARE_INFO = {
    'algorithm': "eos:nearest_neighbor",
    'software_version': measures.__version__,
    'software_title': "WVCC MEaSUREs python library v%s" % measures.__version__,
    'software': "eos:WVCC-MEaSUREs-python-library-%s" % measures.__version__,
}


MATCHUP_INFO = {
    'level': "L2",
    'version': app.config['MATCHUP_VERSION'],
    'doi': "doi:10.5067/MEASURES/WVCC/DATA204",
    'short_name': "AIRS_CPR_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection': "wvcc:AIRS_CPR_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection_label': "AIRS-CloudSat cloud mask and radar reflectivities collocation indexes v%s" % app.config['MATCHUP_VERSION'],
    'collection_loc': "http://disc.gsfc.nasa.gov/datacollection/AIRS_CPR_IND_V4.0.html",
}


MERGED_DATA_INFO = {
    'level': "L2",
    'version': app.config['MERGED_DATA_VERSION'],
    'doi': "doi:10.5067/MEASURES/WVCC/DATA205",
    'short_name': "AIRS_CPR_MAT-%s" % app.config['MERGED_DATA_VERSION'],
    'collection': "wvcc:AIRS_CPR_MAT-%s" % app.config['MERGED_DATA_VERSION'],
    'collection_label': "AIRS-CloudSat cloud mask, radar reflectivities, and cloud classification matchups v%s" % app.config['MERGED_DATA_VERSION'],
    'collection_loc': "http://disc.gsfc.nasa.gov/datacollection/AIRS_CPR_MAT_V4.0.html",
}


CAL_MATCHUP_INFO = {
    'level': "L2",
    'version': app.config['MATCHUP_VERSION'],
    'doi': "doi:10.5067/MEASURES/WVCC/DATA207",
    'short_name': "AIRS_CPR_CAL_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection': "wvcc:AIRS_CPR_CAL_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection_label': "AIRS-CloudSat-CALIPSO cloud mask and radar reflectivities collocation indexes v%s" % app.config['MATCHUP_VERSION'],
    'collection_loc': "http://disc.gsfc.nasa.gov/datacollection/AIRS_CPR_CAL_IND_V4.0.html",
}


MYD_MATCHUP_INFO = {
    'level': "L2",
    'version': app.config['MATCHUP_VERSION'],
    'doi': "doi:10.5067/MEASURES/WVCC/DATA206",
    'short_name': "AIRS_MDS_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection': "wvcc:AIRS_MDS_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection_label': "AIRS-MODIS collocation indexes v%s" % app.config['MATCHUP_VERSION'],
    'collection_loc': "http://disc.gsfc.nasa.gov/datacollection/AIRS_MDS_IND_V4.html",
}


MLS_MATCHUP_INFO = {
    'level': "L2",
    'version': app.config['MATCHUP_VERSION'],
    'doi': "doi:10.5067/MEASURES/WVCC/DATA209",
    'short_name': "AIRS_MLS_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection': "wvcc:AIRS_MLS_IND-%s" % app.config['MATCHUP_VERSION'],
    'collection_label': "AIRS-MLS collocation indexes v%s" % app.config['MATCHUP_VERSION'],
    'collection_loc': "http://disc.gsfc.nasa.gov/datacollection/AIRS_MLS_IND_V4.html",
}
