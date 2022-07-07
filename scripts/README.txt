AIRS-CloudSat Matchup Indices
-----------------------------
./generate_airs_cloudsat_matchup.sh http://airspar1u.ecs.nasa.gov/opendap/Aqua_AIRS_Level2/AIRX2RET.006/2006/359/AIRS.2006.12.25.001.L2.RetStd.v6.0.7.0.G13152123955.hdf


AIRS-CloudSat Merged Data
-------------------------
./generate_airs_cloudsat_merged_data.sh index-airs.aqua_cloudsat-v4.0-2006.12.25.001/index-airs.aqua_cloudsat-v4.0-2006.12.25.001.nc4 varlist_v4.0-filtered.json 


AIRS-CloudSat-CALIPSO Matchup Indices
-------------------------------------
./generate_airs_cloudsat_calipso_matchup.sh index-airs.aqua_cloudsat-v4.0-2006.12.25.001.nc4 http://cvo.hysds.net:8080/opendap/caliop.calipso/333mCLay


AIRS/MODIS/AMSR-E Matchup Indices
-------------------------------------
./generate_airs_modis_amsre_matchup.sh f32_20020715v7.gz index-airs.aqua_modis.aqua-v1.0-2003.01.05.0000.nc4 index-airs.aqua_modis.aqua-v1.0-2003.01.05.0000.met.json


AIRS/MODIS/AMSR-2 Matchup Indices
-------------------------------------
./generate_airs_modis_amsr2_matchup.sh f34_20140301v7.2.gz index-airs.aqua_modis.aqua-v1.0-2014.03.01.0000.nc4 index-airs.aqua_modis.aqua-v1.0-2014.03.01.0000.met.json
