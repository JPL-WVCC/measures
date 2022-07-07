#	This routine reads version-7 RSS AMSR-E time-averaged files 
#	The time-averaged files include:
#   3-day	(average of 3 days ending on file date),  satname_yyyymmddv7_d3d.gz
#   weekly	(average of 7 days ending on Saturday of file date),  satname_yyyymmddv7.gz
#   monthly	(average of all days in month),  satname_yyyymmv7.gz
#	 	where satname  = name of satellite (amsre or amsr)
#	       yyyy		= year
#		   mm		= month
#		   dd		= day of month
#
#   missing = fill value used for missing data;
#                  if None, then fill with byte codes (251-255)

#	the output values correspond to:
#	sst			sea surface temperature in deg Celsius
#	windLF		10m surface wind, low frequency, in meters/second
#	windMF		10m surface wind, medium frequency, in meters/second
#	vapor		columnar or integrated water vapor in millimeters
#	cloud		cloud liquid water in millimeters
#	rain		rain rate in millimeters/hour
#   longitude	Grid Cell Center Longitude', LON = 0.25*x_grid_location - 0.125 degrees east
#   latitude	Grid Cell Center Latitude',  LAT = 0.25*y_grid_location - 90.125
#   land		Is this land?
#   ice			Is this ice?
#   nodata		Is there no data
#

from . bytemaps import sys
from . bytemaps import Dataset
from . bytemaps import Verify


class AMSREaveraged(Dataset):
    """ Read averaged AMSRE bytemaps. """
    """
    Public data:
        filename = name of data file
        missing = fill value used for missing data;
                  if None, then fill with byte codes (251-255)
        dimensions = dictionary of dimensions for each coordinate
        variables = dictionary of data for each variable
    """

    def __init__(self, filename, missing=None):
        """
        Required arguments:
            filename = name of data file to be read (string)
                
        Optional arguments:
            missing = fill value for missing data,
                      default is the value used in verify file
        """       
        self.filename = filename
        self.missing = missing
        Dataset.__init__(self)

    # Dataset:

    def _attributes(self):
        return ['coordinates','long_name','units','valid_min','valid_max']

    def _coordinates(self):
        return ('variable','latitude','longitude')

    def _shape(self):
        return (6,720,1440)

    def _variables(self):
        return ['sst','windLF','windMF','vapor','cloud','rain',
                'longitude','latitude','land','ice','nodata']

    # _default_get():  

    def _get_index(self,var):
        return {'sst' : 0,
                'windLF' : 1,
                'windMF' : 2,
                'vapor' : 3,
                'cloud' : 4,
                'rain' : 5,
                }[var]

    def _get_offset(self,var):
        return {'sst' : -3.0,
                'cloud' : -0.05,
                }[var]

    def _get_scale(self,var):
        return {'sst' : 0.15,
                'windLF' : 0.2,
                'windMF' : 0.2,
                'vapor' : 0.3,
                'cloud' : 0.01,
                'rain' : 0.1,
                }[var]

    # _get_ attributes:

    def _get_long_name(self,var):
        return {'sst' : 'Sea Surface Temperature',
                'windLF' : '10m Surface Wind Speed (low frequency)',
                'windMF' : '10m Surface Wind Speed (medium frequency)',
                'vapor' : 'Columnar Water Vapor',
                'cloud' : 'Cloud Liquid Water',
                'rain'  :'Surface Rain Rate',
                'longitude' : 'Grid Cell Center Longitude',
                'latitude' : 'Grid Cell Center Latitude',
                'land' : 'Is this land?',
                'ice' : 'Is this ice?',
                'nodata' : 'Is there no data?',
                }[var]

    def _get_units(self,var):
        return {'sst' : 'deg Celsius',
                'windLF' : 'm/s',
                'windMF' : 'm/s',
                'vapor' : 'mm',
                'cloud' : 'mm',
                'rain' : 'mm/hr',
                'longitude' : 'degrees east',
                'latitude' : 'degrees north',
                'land' : 'True or False',
                'ice' : 'True or False',
                'nodata' : 'True or False',
                }[var]

    def _get_valid_min(self,var):
        return {'sst' : -3.0,
                'windLF' : 0.0,
                'windMF' : 0.0,
                'vapor' : 0.0,
                'cloud' : -0.05,
                'rain' : 0.0,
                'longitude' : 0.0,
                'latitude' : -90.0,
                'land' : False,
                'ice' : False,
                'nodata' : False,
                }[var]

    def _get_valid_max(self,var):
        return {'sst' : 34.5,
                'windLF' : 50.0,
                'windMF' : 50.0,
                'vapor' : 75.0,
                'cloud' : 2.45,
                'rain' : 25.0,
                'longitude' : 360.0,
                'latitude' : 90.0,
                'land' : True,
                'ice' : True,
                'nodata' : True,
                }[var]


class ThreedayVerify(Verify):
    """ Contains info for verification. """
    
    def __init__(self,dataset):
        self.filename = 'verify_amsre_v7.txt'
        self.ilon1 = 170
        self.ilon2 = 175
        self.ilat1 = 274
        self.ilat2 = 278                
        self.variables = ['sst','windLF','windMF','vapor','cloud','rain']
        self.startline = {'sst' : 126,
                          'windLF' : 133,
                          'windMF' : 140,
                          'vapor' : 147,
                          'cloud' : 154,
                          'rain' : 161 }
        Verify.__init__(self,dataset)
        

class WeeklyVerify(Verify):
    """ Contains info for verification. """
    
    def __init__(self,dataset):
        self.filename = 'verify_amsre_v7.txt'
        self.ilon1 = 170
        self.ilon2 = 175
        self.ilat1 = 274
        self.ilat2 = 278                
        self.variables = ['sst','windLF','windMF','vapor','cloud','rain']
        self.startline = {'sst' : 172,
                          'windLF' : 179,
                          'windMF' : 186,
                          'vapor' : 193,
                          'cloud' : 200,
                          'rain' : 207 }
        Verify.__init__(self,dataset)
        

class MonthlyVerify(Verify):
    """ Contains info for verification. """
    
    def __init__(self,dataset):
        self.filename = 'verify_amsre_v7.txt'
        self.ilon1 = 170
        self.ilon2 = 175
        self.ilat1 = 274
        self.ilat2 = 278                
        self.variables = ['sst','windLF','windMF','vapor','cloud','rain']
        self.startline = {'sst' : 218,
                          'windLF' : 225,
                          'windMF' : 232,
                          'vapor' : 239,
                          'cloud' : 246,
                          'rain' : 253 }
        Verify.__init__(self,dataset)
        

if __name__ == '__main__':
    """ Automated testing. """    

    # read 3-day averaged:
    amsr = AMSREaveraged('f32_20020715v7_d3d.gz')
    if not amsr.variables: sys.exit('file not found')

    # verify 3-day:
    verify = ThreedayVerify(amsr)
    if verify.success: print('successful verification for 3-day')
    else: sys.exit('verification failed for 3-day')
    print('')

    # read weekly averaged:
    amsr = AMSREaveraged('f32_20020720v7.gz')
    if not amsr.variables: sys.exit('file not found')

    # verify weekly:
    verify = WeeklyVerify(amsr)
    if verify.success: print('successful verification for weekly')
    else: sys.exit('verification failed for weekly')     
    print('')
    
    # read monthly averaged:
    amsr = AMSREaveraged('f32_200207v7.gz')
    if not amsr.variables: sys.exit('file not found')
    
    # verify:
    verify = MonthlyVerify(amsr)
    if verify.success: print('successful verification for monthly')
    else: sys.exit('verification failed for monthly')      
    print('')
    
    print('all tests completed successfully')
    print ('')
