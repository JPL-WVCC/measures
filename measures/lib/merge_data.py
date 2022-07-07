import os, sys, re, time, json, requests, shutil, logging
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
from pydap.client import open_url
import pydap.lib
import numpy as np
from pprint import pformat
from datetime import datetime, timedelta
from netCDF4 import Dataset
from SOAPpy.WSDL import Proxy

from prov_es.model import get_uuid, ProvEsDocument

from measures import app
from .xml import get_etree, get_nsmap
from .prov_info import (AIRS_GRANULE_RE, CS_GRANULE_RE, AIRS_METADATA_MAP,
CS_METADATA_MAP, ADDITIONAL_NAMESPACES, AIRS_COLLECTION_INFO,
CLOUDSAT_COLLECTION_INFO, SOFTWARE_INFO, MATCHUP_INFO, MERGED_DATA_INFO)


# cache DAP calls (debug)
#pydap.lib.CACHE = "/tmp/pydap-cache/"


def merge_airs_cloudsat(matchup_file, varlist_json_file, merged_file,
                        airs_version="v6",
                        airs_l1_version="v5",
                        #airs_url_match="http://msas-dap\.jpl\.nasa\.gov/opendap",
                        airs_url_match="\.gesdisc\.eosdis\.nasa\.gov/opendap",
                        cloudsat_url_match="http://cvo\.hysds\.net:8080/opendap/.*\.hdf$",
                        s3_airs_url_match="http://cvo\.hysds\.net:8080/opendap/.*\.hdf$"):
                        #cloudsat_url_match="http://cvo\.hysds\.net:8080/s3/dap/atrain/.*\.hdf$"):
                        #cloudsat_url_match="http://cvo\.jpl\.nasa\.gov:8080/opendap/.*\.hdf$"):
    """Merge AIRS and CloudSat data using the matchup indices file
       and the varlist JSON configuration passed."""

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
    doc.platform(airs_platform, [airs_instrument], label=airs_platform_title)
    doc.instrument(airs_instrument, airs_platform, [airs_sensor], [airs_gov_org],
                   label=airs_instrument_title)
    doc.sensor(airs_sensor, airs_instrument, label=airs_sensor_title)

    # PROV-ES values for CloudSat input
    cs_platform = CLOUDSAT_COLLECTION_INFO['platform']
    cs_platform_title = CLOUDSAT_COLLECTION_INFO['platform_title']
    cs_instrument = CLOUDSAT_COLLECTION_INFO['instrument']
    cs_instrument_title = CLOUDSAT_COLLECTION_INFO['instrument_title']
    cs_sensor = CLOUDSAT_COLLECTION_INFO['sensor']
    cs_sensor_title = CLOUDSAT_COLLECTION_INFO['sensor_title']
    cs_gov_org = CLOUDSAT_COLLECTION_INFO['gov_org']
    cs_gov_org_title = CLOUDSAT_COLLECTION_INFO['gov_org_title']
    cs_access_url = CLOUDSAT_COLLECTION_INFO['access_url']
    if cs_gov_org != airs_gov_org:
        doc.governingOrganization(cs_gov_org, label=cs_gov_org_title)
    doc.platform(cs_platform, [cs_instrument], label=cs_platform_title)
    doc.instrument(cs_instrument, cs_platform, [cs_sensor], [cs_gov_org],
                   label=cs_instrument_title)
    doc.sensor(cs_sensor, cs_instrument, label=cs_sensor_title)

    # PROV-ES values for WVCC matchup software
    algorithm = SOFTWARE_INFO['algorithm']
    software_version = SOFTWARE_INFO['software_version']
    software_title = SOFTWARE_INFO['software_title']
    software = SOFTWARE_INFO['software']
    doc.software(software, [algorithm], software_version, label=software_title)

    # PROV-ES for input matchup index file and collection
    doc.collection(MATCHUP_INFO['collection'], MATCHUP_INFO['doi'],
                   MATCHUP_INFO['short_name'], MATCHUP_INFO['collection_label'],
                   [MATCHUP_INFO['collection_loc']], [airs_instrument, cs_instrument],
                   MATCHUP_INFO['level'], MATCHUP_INFO['version'],
                   label=MATCHUP_INFO['collection_label'])
    matchup_file_ent = doc.granule("hysds:%s" % get_uuid(matchup_file),
                                   MATCHUP_INFO['doi'], [os.path.abspath(matchup_file)],
                                   [airs_instrument, cs_instrument],
                                   MATCHUP_INFO['collection'],
                                   MATCHUP_INFO['level'], MATCHUP_INFO['version'],
                                   label=os.path.basename(matchup_file))
    input_ids[matchup_file_ent.identifier] = True

    # PROV-ES values for WVCC merged data file and collection
    wvcc_level = MERGED_DATA_INFO['level']
    wvcc_version = MERGED_DATA_INFO['version']
    wvcc_doi = MERGED_DATA_INFO['doi']
    wvcc_short_name = MERGED_DATA_INFO['short_name']
    wvcc_collection = MERGED_DATA_INFO['collection']
    wvcc_collection_label = MERGED_DATA_INFO['collection_label']
    wvcc_collection_loc = MERGED_DATA_INFO['collection_loc']
    doc.collection(wvcc_collection, wvcc_doi, wvcc_short_name, wvcc_collection_label,
                   [wvcc_collection_loc], [airs_instrument, cs_instrument],
                   wvcc_level, wvcc_version, label=wvcc_collection_label)
    merged_file_ent = doc.granule("hysds:%s" % get_uuid(merged_file),
                                   wvcc_doi, [os.path.abspath(merged_file)],
                                   [airs_instrument, cs_instrument],
                                   wvcc_collection, wvcc_level, wvcc_version,
                                   label=os.path.basename(merged_file))
    output_ids[merged_file_ent.identifier] = True
    
    # create dict indexed by instruments
    with open(varlist_json_file) as f:
        varlist_cfg = json.load(f)
    varlist_dict = dict([(i["instrument"], i["datasets"]) for i in varlist_cfg])
    varlist_ent = doc.file("hysds:%s" % get_uuid(varlist_json_file),
                           [os.path.abspath(varlist_json_file)],
                           label=os.path.basename(varlist_json_file))
    input_ids[varlist_ent.identifier] = True
    #print(pformat(varlist_dict))

    # copy matchup file to merged data file
    shutil.copy(matchup_file, merged_file)

    # open up merged data file
    root_grp = Dataset(merged_file, 'a')

    # get AIRS id
    airs_id = root_grp.AIRS_FILE[0:19]
    logging.debug("airs_id: %s" % airs_id)

    # update root metadata
    del root_grp.AIRS_DAP_URL
    root_grp.VERSION = app.config['MERGED_DATA_VERSION']
    root_grp.PRODUCTIONDATE = datetime.utcnow().isoformat('T')
    root_grp.IDENTIFIER_PRODUCT_DOI = wvcc_doi
    root_grp.IDENTIFIER_PRODUCT_DOI_AUTHORITY = "http://dx.doi.org/"

    # get number of matchups
    total = len(root_grp.dimensions['matchup'])
    logging.debug("total matchups: %d" % total)

    # get airs/amsu/amsugeotrack indices; cloudsat by airs and amsu
    airs_idcs = set()
    amsu_idcs = set()
    amsu_track_idcs = set()
    cs_idcs = root_grp.variables['cloudsat_idx']
    cs_files = root_grp.variables['cloudsat_file']
    cs_idcs_by_airs_idc = {}
    cs_idcs_by_amsu_idc = {}
    cs_idcs_by_file = {}
    cs_idcs_by_airs_idc_by_file = {}
    cs_idcs_by_amsu_idc_by_file = {}
    for i, idx in enumerate(root_grp.variables['airs_idx']):
        airs_idx = tuple(idx)
        amsu_idx = tuple(idx[0:2])
        airs_idcs.add(airs_idx)
        amsu_idcs.add(amsu_idx)
        amsu_track_idcs.add(idx[0])
        cs_idcs_by_airs_idc.setdefault(airs_idx, []).append(cs_idcs[i])
        cs_idcs_by_amsu_idc.setdefault(amsu_idx, []).append(cs_idcs[i])
        cs_idcs_by_file.setdefault(cs_files[i], []).append(cs_idcs[i])
        cs_idcs_by_airs_idc_by_file.setdefault(airs_idx, {}).setdefault(cs_files[i], []).append(cs_idcs[i])
        cs_idcs_by_amsu_idc_by_file.setdefault(amsu_idx, {}).setdefault(cs_files[i], []).append(cs_idcs[i])
    airs_idcs = sorted(airs_idcs)
    amsu_idcs = sorted(amsu_idcs)
    amsu_track_idcs = sorted(amsu_track_idcs)

    # sort cs_idcs by file
    for cs_file in cs_idcs_by_file:
        cs_idcs_by_file[cs_file] = sorted(cs_idcs_by_file[cs_file])

    # create groups for matchups by resolution
    airs_grp = root_grp.createGroup('AIRS')
    airs_res_grp = airs_grp.createGroup('AIRS_resolution')
    amsu_res_grp = airs_grp.createGroup('AMSU_resolution')

    # create dimensions for both groups
    root_grp.createDimension('amsu_matchup', len(amsu_idcs))
    root_grp.createDimension('amsu_track_matchup', len(amsu_track_idcs))
    root_grp.createDimension('airs_matchup', len(airs_idcs))

    # get AIRS L2 DAP urls
    p = Proxy(app.config['GRQ_URL'])
    res_xml = p.findDataById([airs_id], None, airs_version)
    #print(res_xml)
    root = get_etree(res_xml)
    nsmap = get_nsmap(res_xml)
    airs_url_re = re.compile(airs_url_match)
    s3_airs_url_re = re.compile(s3_airs_url_match)
    airs_dap_urls_used = {}
    airs_dap_urls = {}
    for i in root.xpath('.//_:url/text()', namespaces=nsmap):
        if s3_airs_url_re.search(i):
            if 'RetStd' in i:
                airs_dap_urls['L2_Standard_atmospheric&surface_product'] = open_url(i)
                if i not in airs_dap_urls_used:
                    airs_dap_urls_used[i] = True
            if 'RetSup' in i:
                airs_dap_urls['L2_Support_atmospheric&surface_product'] = open_url(i)
                if i not in airs_dap_urls_used:
                    airs_dap_urls_used[i] = True

    # get AIRS L1 DAP urls
    res_xml = p.findDataById([airs_id], None, airs_l1_version)
    root = get_etree(res_xml)
    nsmap = get_nsmap(res_xml)
    for i in root.xpath('.//_:url/text()', namespaces=nsmap):
        if airs_url_re.search(i):
            if 'L1B.AIRS_Rad' in i:
                airs_dap_urls['L1B_AIRS_Science'] = open_url(i)
                if i not in airs_dap_urls_used:
                    airs_dap_urls_used[i] = True
            else: pass
    #print(pformat(airs_dap_urls))

    # get cloudsat dap urls
    cs_dap_urls_used = {}
    cs_dap_urls = {}
    cs_ids = []
    cs_url_re = re.compile(cloudsat_url_match)
    for cs_file in cs_files:
        cs_id = cs_file[0:22]
        cs_ids.append(cs_id)
        if cs_file in cs_dap_urls: continue
        res_xml = p.findDataById([cs_id], None, None)
        root = get_etree(res_xml)
        nsmap = get_nsmap(res_xml)
        cs_dap_urls[cs_file] = {
            '2C-PRECIP-COLUMN': None,
            '2B-CLDCLASS': None,
            '2B-CWC-RO': None,
            '2B-GEOPROF-LIDAR': None,
            '2B-GEOPROF': None,
            '2B-TAU': None,
        }
        for i in root.xpath('.//_:url/text()', namespaces=nsmap):
            if cs_url_re.search(i):
                for k in cs_dap_urls[cs_file]:
                    match_cs_prod = re.search(r'_CS_(.*?)_GRANULE', i)
                    if match_cs_prod is None:
                        raise RuntimeError("Failed to detect CloudSat product type: %s" % i)
                    if match_cs_prod.group(1) == k:
                        cs_dap_urls[cs_file][k] = open_url(i)
                        if i not in cs_dap_urls_used:
                            cs_dap_urls_used[i] = True
        show_xml = False
        for k,v in cs_dap_urls[cs_file].iteritems():
            if v is None:
                logging.warning("No dap url found for dataset %s for %s." % (k, cs_file))
                show_xml = True
        if show_xml: logging.warning("res_xml: %s" % res_xml)
    #logging.warning(pformat(cs_dap_urls))

    # create idc arrays
    airs_idcs = np.array(airs_idcs)
    amsu_idcs = np.array(amsu_idcs)

    # AIRS datasets to do
    datasets_to_do = [
        'L2_Standard_atmospheric&surface_product',
        'L2_Support_atmospheric&surface_product',
        'L1B_AIRS_Science',
    ]

    # create dimensions and variables for AIRS RetStd, RetSup, and Radiances
    amsu_res_grp.createGroup('L2_Standard_atmospheric&surface_product')
    airs_res_grp.createGroup('L2_Standard_atmospheric&surface_product')
    amsu_res_grp.createGroup('L2_Support_atmospheric&surface_product')
    airs_res_grp.createGroup('L2_Support_atmospheric&surface_product')
    airs_res_grp.createGroup('L1B_AIRS_Science')
    for ds in varlist_dict['AIRS']:
        if ds['dataset'] in datasets_to_do:
            for v in ds['variables']:
                #print(v)
                matched = None
                actual_varname = None
                for dap_var in airs_dap_urls[ds['dataset']].keys():
                    if v == dap_var:
                        #print("matched %s for %s" % (dap_var, v))
                        matched = v
                        actual_varname = dap_var
                        break
                    else:
                        # construct possible var names
                        for field_type in ['Geolocation_Fields', 'Data_Fields']:
                            ft_var = "%s_%s_%s" % (ds['dataset'], field_type, v)
                            if ft_var == dap_var:
                                matched = v
                                actual_varname = ft_var
                                break
                        if matched is not None: break
                        ft_var = "vdata_%s_Data_Fields_%s_vdf_%s" % (ds['dataset'], v, v)
                        if ft_var == dap_var:
                            matched = v
                            actual_varname = ft_var
                            break
                if matched is None:
                    logging.warning("Found no match for variable %s for AIRS %s." % (v, ds['dataset']))
                else:
                    dap_var = airs_dap_urls[ds['dataset']][actual_varname]

                    # create dimensions
                    dim_dict = dict(zip(dap_var.dimensions, dap_var.shape))
                    for dim in dim_dict:
                        #print("%s: %d" % (dim, dim_dict[dim]))
                        if dim not in airs_grp.dimensions:
                            airs_grp.createDimension(dim, dim_dict[dim])

                    # create var
                    #print("%s: %s %s" % (matched, dap_var.shape, dap_var.dimensions))
                    if len(dap_var.shape) >= 4 and dap_var.shape[0:4] == (45, 30, 3, 3):
                        dims = ['airs_matchup']
                        dims.extend(dap_var.dimensions[4:])
                        dims = tuple(dims)
                        grp = airs_res_grp.groups[ds['dataset']]

                        # inefficient; downloads whole array over the wire
                        #data = dap_var[:][(airs_idcs[:,0], airs_idcs[:,1], airs_idcs[:,2], airs_idcs[:,3])]

                        # instead, download the smallest possible slice then use numpy fancy indexing
                        min_0 = np.min(airs_idcs[:,0]); max_0 = np.max(airs_idcs[:,0]) + 1
                        min_1 = np.min(airs_idcs[:,1]); max_1 = np.max(airs_idcs[:,1]) + 1
                        min_2 = np.min(airs_idcs[:,2]); max_2 = np.max(airs_idcs[:,2]) + 1
                        min_3 = np.min(airs_idcs[:,3]); max_3 = np.max(airs_idcs[:,3]) + 1
                        tmp_data = dap_var[min_0:max_0, min_1:max_1, min_2:max_2, min_3:max_3]
                        data = tmp_data[(airs_idcs[:,0]-min_0,
                                         airs_idcs[:,1]-min_1,
                                         airs_idcs[:,2]-min_2,
                                         airs_idcs[:,3]-min_3)]
                    elif len(dap_var.shape) >= 2 and dap_var.shape[0:2] == (45, 30):
                        dims = ['amsu_matchup']
                        dims.extend(dap_var.dimensions[2:])
                        dims = tuple(dims)
                        grp = amsu_res_grp.groups[ds['dataset']]

                        # inefficient; downloads whole array over the wire
                        #data = dap_var[:][(amsu_idcs[:,0], amsu_idcs[:,1])]

                        # instead, download the smallest possible slice then use numpy fancy indexing
                        min_0 = np.min(amsu_idcs[:,0]); max_0 = np.max(amsu_idcs[:,0]) + 1
                        min_1 = np.min(amsu_idcs[:,1]); max_1 = np.max(amsu_idcs[:,1]) + 1
                        tmp_data = dap_var[min_0:max_0, min_1:max_1]
                        data = tmp_data[(amsu_idcs[:,0]-min_0, amsu_idcs[:,1]-min_1)]
                    elif len(dap_var.shape) >= 2 and dap_var.shape[0:2] == (135, 90):
                        dims = ['airs_matchup']
                        dims.extend(dap_var.dimensions[2:])
                        dims = tuple(dims)
                        grp = airs_res_grp.groups[ds['dataset']]

                        tmp_idcs = [(airs_idc[0]*3+airs_idc[2], airs_idc[1]*3+airs_idc[3]) for airs_idc in airs_idcs]
                        tmp_idcs = np.array(tmp_idcs)

                        # inefficient; downloads whole array over the wire
                        #data = dap_var[:][(tmp_idcs[:,0], tmp_idcs[:,1])]

                        # instead, download the smallest possible slice then use numpy fancy indexing
                        min_0 = np.min(tmp_idcs[:,0]); max_0 = np.max(tmp_idcs[:,0]) + 1
                        min_1 = np.min(tmp_idcs[:,1]); max_1 = np.max(tmp_idcs[:,1]) + 1
                        tmp_data = dap_var[min_0:max_0, min_1:max_1]
                        data = tmp_data[(tmp_idcs[:,0]-min_0, tmp_idcs[:,1]-min_1)]
                    elif len(dap_var.shape) == 1:
                        dims = dap_var.dimensions
                        grp = airs_grp
                        data = dap_var[:]
                    else:
                        logging.warning("Skipping variable %s %s %s." % (matched, dap_var.dimensions, dap_var.shape))
                        continue

                    # error if variable exists already
                    if matched in grp.variables:
                        logging.warning("Variable %s already in group %s. Skipping." % (matched, grp))
                        continue

                    # create variable
                    if '_FillValue' in dap_var.attributes:
                        v = grp.createVariable(matched, dap_var.type.typecode, dims,
                                               fill_value=dap_var.attributes['_FillValue'],
                                               zlib=True)
                    else:
                        v = grp.createVariable(matched, dap_var.type.typecode, dims, zlib=True)
                    for at_name, at_val in dap_var.attributes.items():
                        if at_name == '_FillValue': continue
                        setattr(v, at_name, at_val)
                    logging.debug("%s: %s %s %s" % (matched, dap_var.shape, dims, dap_var.attributes))

                    # set version
                    if ds['dataset'].startswith('L1'):
                        setattr(v, 'AIRS_version', airs_l1_version)
                    else: setattr(v, 'AIRS_version', airs_version)
                    
                    # populate variable with data
                    try:
                        v[:] = data
                    except Exception, e:
                        logging.error("Got error setting variable data: %s" % e)
                        continue

    # create groups for CloudSat matchups by resolution
    cs_grp = root_grp.createGroup('CloudSat')
    cs_airs_res_grp = cs_grp.createGroup('AIRS_resolution')
    cs_amsu_res_grp = cs_grp.createGroup('AMSU_resolution')

    # loop over airs and amsu idcs
    for res_info in ((amsu_idcs, cs_idcs_by_amsu_idc, cs_idcs_by_amsu_idc_by_file, 'amsu_matchup', cs_amsu_res_grp), 
                     (airs_idcs, cs_idcs_by_airs_idc, cs_idcs_by_airs_idc_by_file, 'airs_matchup', cs_airs_res_grp)):

        # handle each AIRS resolution type
        idc_set, cs_by_idc, cs_by_idc_by_file, res_dim, res_grp = res_info

        #create cloudsat index dimension
        max_cs_idcs = 0
        for this_idc_set in idc_set:
            this_idc_set = tuple(this_idc_set)
            if len(cs_by_idc[this_idc_set]) > max_cs_idcs:
                max_cs_idcs = len(cs_by_idc[this_idc_set])
        res_grp.createDimension('cs_idx', max_cs_idcs)

        # CloudSat datasets to do
        cs_datasets_to_do = [
            '2B-GEOPROF',
            '2B-GEOPROF-LIDAR',
            '2B-CLDCLASS',
            '2B-CWC-RO',
            '2B-PRECIP-COLUMN',
            '2B-TAU',
        ]
        for ds in varlist_dict['CloudSat']:
            if ds['dataset'] in cs_datasets_to_do:
                ds_grp = res_grp.createGroup(ds['dataset'])
                cs_dap_url = cs_dap_urls[cs_files[0]][ds['dataset']]
                for v in ds['variables']:
                    matched = None
                    actual_varname = None
                    if cs_dap_url is not None:
                        for dap_var in cs_dap_url.keys():
                            if v == dap_var:
                                #logging.warning("matched %s for %s" % (dap_var, v))
                                matched = v
                                actual_varname = dap_var
                                break
                            else:
                                # construct possible var names
                                for field_type in ['Geolocation_Fields', 'Data_Fields']:
                                    ft_var = "%s_%s_%s" % (ds['dataset'], field_type, v)
                                    if ft_var == dap_var:
                                        matched = v
                                        actual_varname = ft_var
                                        break
                                if matched is not None: break
                                ft_var = "vdata_%s_Data_Fields_%s_vdf_%s" % (ds['dataset'], v, v)
                                if ft_var == dap_var:
                                    matched = v
                                    actual_varname = ft_var
                                    break
                    if matched is None:
                        logging.warning("Found no match for variable %s for CloudSat %s." % (v, ds['dataset']))
                        continue

                    # get dap variable for dimension and variable creation
                    dap_var = cs_dap_urls[cs_files[0]][ds['dataset']][actual_varname]
    
                    # create dimensions
                    dim_dict = dict(zip(dap_var.dimensions, dap_var.shape))
                    #print dap_var, dim_dict
                    for dim in dim_dict:
                        if dim not in cs_grp.dimensions:
                            cs_grp.createDimension(dim, dim_dict[dim])
                            #print("created dim %s: %d" % (dim, dim_dict[dim]))

                    # create var
                    #print("%s: %s %s" % (matched, dap_var.shape, dap_var.dimensions))
                    if len(dap_var.shape) == 1: 
                        if dap_var.shape[0] == 1:
                            #dims = [res_dim]
                            continue
                        else: dims = [res_dim, 'cs_idx']
                    elif len(dap_var.shape) >= 2: 
                        dims = [res_dim, 'cs_idx']
                        dims.extend(dap_var.dimensions[1:])
                        dims = tuple(dims)
                    else:
                        logging.warning("Skipping variable %s %s %s." % (matched, dap_var.dimensions, dap_var.shape))
                        continue

                    # error if variable exists already
                    if matched in ds_grp.variables:
                        logging.warning("Variable %s already in group %s. Skipping." % (matched, ds_grp))
                        continue

                    # create variable
                    if '_FillValue' in dap_var.attributes:
                        v = ds_grp.createVariable(matched, dap_var.type.typecode, dims,
                                                  fill_value=dap_var.attributes['_FillValue'],
                                                  zlib=True)
                    else:
                        v = ds_grp.createVariable(matched, dap_var.type.typecode, dims, zlib=True)
                    for at_name, at_val in dap_var.attributes.items():
                        if at_name == '_FillValue': continue
                        setattr(v, at_name, at_val)
                    logging.debug("%s: %s %s %s" % (matched, dap_var.shape, dims, dap_var.attributes))

                    # pull data in one call
                    var_data_by_file = {}
                    for cs_file in sorted(cs_idcs_by_file):
                        dap_var = cs_dap_urls[cs_file][ds['dataset']][matched]
                        this_cs_idcs = np.array(cs_idcs_by_file[cs_file])
                        min_0 = np.min(this_cs_idcs); max_0 = np.max(this_cs_idcs) + 1
                        var_data_by_file[cs_file] = {
                            'data': dap_var[min_0:max_0],
                            'min_0': min_0,
                            'max_0': max_0,
                        }

                    # populate variable with data
                    for i, this_idc_set in enumerate(idc_set):
                        this_idc_set = tuple(this_idc_set)
                        last_cs_idx = 0
                        for cs_file in sorted(cs_by_idc_by_file[this_idc_set]):
                            dap_var = var_data_by_file[cs_file]
                            this_cs_idcs = np.array(cs_by_idc_by_file[this_idc_set][cs_file])
                            data = dap_var['data'][(this_cs_idcs-dap_var['min_0'])]
                            #print data.shape, data
                            try:
                                #print "populating %s[%d, %d:%d]" % (matched, i, last_cs_idx, last_cs_idx+len(data))
                                v[i, last_cs_idx:last_cs_idx+len(data)] = data
                                last_cs_idx += len(data)
                            except Exception, e:
                                #print "Got error setting variable data: %s" % e
                                #continue
                                raise

    # close file
    root_grp.close()

    # create PROV-ES for AIRS dap urls
    airs_cols = {}
    for airs_dap_url in airs_dap_urls_used:
        match = AIRS_GRANULE_RE.search(airs_dap_url)
        if not match:
            raise RuntimeError("Failed to match AIRS granule regex: %s" % airs_dap_url)
        a_yy, a_mm, a_dd, a_gran, a_lev, a_prod, a_vers = match.groups()
        a_doi = AIRS_METADATA_MAP.get(a_prod, {}).get('doi', None)
        a_short_name = AIRS_METADATA_MAP.get(a_prod, {}).get('name', None)
        a_label = AIRS_METADATA_MAP.get(a_prod, {}).get('label', None)
        a_loc = AIRS_METADATA_MAP.get(a_prod, {}).get('location', None)
        if a_loc is None: a_loc = []
        else: a_loc = [a_loc]
        if a_doi not in airs_cols:
            doc.collection(a_doi, a_doi, a_short_name, a_label, a_loc, [airs_instrument],
                           a_lev, a_vers, label=a_label)
            airs_cols[a_doi] = True
        airs_ds = doc.granule('hysds:%s' % get_uuid(airs_dap_url), a_doi,
                          [airs_dap_url], [airs_instrument], a_doi,
                          a_lev, a_vers, label=os.path.basename(airs_dap_url))
        input_ids[airs_ds.identifier] = True

    # create PROV-ES for CS dap urls
    cs_cols = {}
    for cs_dap_url in cs_dap_urls_used:
        match = CS_GRANULE_RE.search(cs_dap_url)
        if not match:
            raise RuntimeError("Failed to match CloudSat granule regex: %s" % cs_dap_url)
        cs_lev, cs_prod, cs_vers = match.groups()
        cs_doi = CS_METADATA_MAP.get(cs_prod, {}).get('doi', None)
        cs_short_name = CS_METADATA_MAP.get(cs_prod, {}).get('name', None)
        cs_label = CS_METADATA_MAP.get(cs_prod, {}).get('label', None)
        cs_loc = CS_METADATA_MAP.get(cs_prod, {}).get('location', None)
        if cs_loc is None: cs_loc = []
        else: cs_loc = [cs_loc]
        cs_col_id = "eos:CloudSat-CPR-%s-%s-%s" % (cs_lev, cs_prod, cs_vers)
        if cs_col_id not in cs_cols:
            doc.collection(cs_col_id, cs_doi, cs_short_name, cs_label, cs_loc,
                           [cs_instrument], cs_lev, cs_vers, label=cs_label)
            cs_cols[cs_col_id] = True
        cs_ds = doc.granule('hysds:%s' % get_uuid(cs_dap_url), cs_doi, [cs_dap_url],
                            [cs_instrument], cs_col_id, cs_lev, cs_vers,
                            label=os.path.basename(cs_dap_url))
        input_ids[cs_ds.identifier] = True

    # create PROV-ES for processStep
    fake_time = datetime.utcnow().isoformat() + 'Z'
    job_id = "generate_airs_cloudsat_merged_data-%s" % fake_time
    doc.processStep('hysds:%s' % get_uuid(job_id), fake_time,
                    fake_time, [software], None, None,
                    input_ids.keys(), output_ids.keys(), label=job_id)

    # dump PROV-ES
    prod_dir = os.path.dirname(merged_file)
    prod_id = os.path.basename(prod_dir)
    prov_es_file = os.path.join(prod_dir, "%s.prov_es.json" % prod_id)
    with open(prov_es_file, 'w') as f:
        json.dump(json.loads(doc.serialize()), f, indent=2, sort_keys=True)
