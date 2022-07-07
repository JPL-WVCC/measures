#!/usr/bin/env python
import os, sys, logging, traceback
from pprint import pprint
try:
    from pydap.util.urs import install_basic_client
    install_basic_client()
except: pass
import pydap.lib
from pydap.client import open_url
import cPickle as pickle

from measures import app
from measures.lib import airs as measures_airs
from measures.lib import cloudsat as measures_cs
from measures.lib.utils import filter_info
from measures.lib.plot import plot_airs_cloudsat_matchup

pydap.lib.CACHE = "/data/work/tmp/pydap_cache/"
pydap.lib.TIMEOUT = 60

logging.basicConfig(level=logging.DEBUG)


# for Chris Wilson who needs matchups for 2013-02-03
airs_dap_url_base = "http://msas-dap.jpl.nasa.gov/opendap/hyrax/repository/products/airs.aqua/v6/2013/02/03/airx2ret/"

airs_files = [
    #'AIRS.2013.02.03.001.L2.RetStd.v6.0.7.0.G13034192549.hdf',
    'AIRS.2013.02.03.002.L2.RetStd.v6.0.7.0.G13034192255.hdf',
    'AIRS.2013.02.03.003.L2.RetStd.v6.0.7.0.G13034191922.hdf',
    'AIRS.2013.02.03.004.L2.RetStd.v6.0.7.0.G13034192218.hdf',
    'AIRS.2013.02.03.005.L2.RetStd.v6.0.7.0.G13034192258.hdf',
    'AIRS.2013.02.03.006.L2.RetStd.v6.0.7.0.G13034193851.hdf',
    'AIRS.2013.02.03.007.L2.RetStd.v6.0.7.0.G13034193843.hdf',
    'AIRS.2013.02.03.008.L2.RetStd.v6.0.7.0.G13034193950.hdf',
    'AIRS.2013.02.03.009.L2.RetStd.v6.0.7.0.G13034194137.hdf',
    'AIRS.2013.02.03.010.L2.RetStd.v6.0.7.0.G13034194159.hdf',
    'AIRS.2013.02.03.011.L2.RetStd.v6.0.7.0.G13034194837.hdf',
    'AIRS.2013.02.03.012.L2.RetStd.v6.0.7.0.G13034195119.hdf',
    'AIRS.2013.02.03.013.L2.RetStd.v6.0.7.0.G13034195046.hdf',
    'AIRS.2013.02.03.014.L2.RetStd.v6.0.7.0.G13034195036.hdf',
    'AIRS.2013.02.03.015.L2.RetStd.v6.0.7.0.G13034195121.hdf',
    'AIRS.2013.02.03.016.L2.RetStd.v6.0.7.0.G13034200647.hdf',
    'AIRS.2013.02.03.017.L2.RetStd.v6.0.7.0.G13034200748.hdf',
    'AIRS.2013.02.03.018.L2.RetStd.v6.0.7.0.G13034200845.hdf',
    'AIRS.2013.02.03.019.L2.RetStd.v6.0.7.0.G13034200532.hdf',
    'AIRS.2013.02.03.020.L2.RetStd.v6.0.7.0.G13034200655.hdf',
    'AIRS.2013.02.03.021.L2.RetStd.v6.0.7.0.G13034202248.hdf',
    'AIRS.2013.02.03.022.L2.RetStd.v6.0.7.0.G13034202243.hdf',
    'AIRS.2013.02.03.023.L2.RetStd.v6.0.7.0.G13034202336.hdf',
    'AIRS.2013.02.03.024.L2.RetStd.v6.0.7.0.G13034202238.hdf',
    'AIRS.2013.02.03.025.L2.RetStd.v6.0.7.0.G13034202250.hdf',
    'AIRS.2013.02.03.026.L2.RetStd.v6.0.7.0.G13034203642.hdf',
    'AIRS.2013.02.03.027.L2.RetStd.v6.0.7.0.G13034203529.hdf',
    'AIRS.2013.02.03.028.L2.RetStd.v6.0.7.0.G13034203710.hdf',
    'AIRS.2013.02.03.029.L2.RetStd.v6.0.7.0.G13034204038.hdf',
    'AIRS.2013.02.03.030.L2.RetStd.v6.0.7.0.G13034204020.hdf',
    'AIRS.2013.02.03.031.L2.RetStd.v6.0.7.0.G13034205354.hdf',
    'AIRS.2013.02.03.032.L2.RetStd.v6.0.7.0.G13034205401.hdf',
    'AIRS.2013.02.03.033.L2.RetStd.v6.0.7.0.G13034205353.hdf',
    'AIRS.2013.02.03.034.L2.RetStd.v6.0.7.0.G13034205448.hdf',
    'AIRS.2013.02.03.035.L2.RetStd.v6.0.7.0.G13034205357.hdf',
    'AIRS.2013.02.03.036.L2.RetStd.v6.0.7.0.G13034210614.hdf',
    'AIRS.2013.02.03.037.L2.RetStd.v6.0.7.0.G13034210739.hdf',
    'AIRS.2013.02.03.038.L2.RetStd.v6.0.7.0.G13034210859.hdf',
    'AIRS.2013.02.03.039.L2.RetStd.v6.0.7.0.G13034210839.hdf',
    'AIRS.2013.02.03.040.L2.RetStd.v6.0.7.0.G13034210737.hdf',
    'AIRS.2013.02.03.041.L2.RetStd.v6.0.7.0.G13034212204.hdf',
    'AIRS.2013.02.03.042.L2.RetStd.v6.0.7.0.G13034212148.hdf',
    'AIRS.2013.02.03.043.L2.RetStd.v6.0.7.0.G13034211935.hdf',
    'AIRS.2013.02.03.044.L2.RetStd.v6.0.7.0.G13034212220.hdf',
    'AIRS.2013.02.03.045.L2.RetStd.v6.0.7.0.G13034212114.hdf',
    'AIRS.2013.02.03.046.L2.RetStd.v6.0.7.0.G13034213754.hdf',
    'AIRS.2013.02.03.047.L2.RetStd.v6.0.7.0.G13034213924.hdf',
    'AIRS.2013.02.03.048.L2.RetStd.v6.0.7.0.G13034213615.hdf',
    'AIRS.2013.02.03.049.L2.RetStd.v6.0.7.0.G13034213614.hdf',
    'AIRS.2013.02.03.050.L2.RetStd.v6.0.7.0.G13034213647.hdf',
    'AIRS.2013.02.03.051.L2.RetStd.v6.0.7.0.G13034215110.hdf',
    'AIRS.2013.02.03.052.L2.RetStd.v6.0.7.0.G13034214921.hdf',
    'AIRS.2013.02.03.053.L2.RetStd.v6.0.7.0.G13034215044.hdf',
    'AIRS.2013.02.03.054.L2.RetStd.v6.0.7.0.G13034215324.hdf',
    'AIRS.2013.02.03.055.L2.RetStd.v6.0.7.0.G13034215253.hdf',
    'AIRS.2013.02.03.056.L2.RetStd.v6.0.7.0.G13034220812.hdf',
    'AIRS.2013.02.03.057.L2.RetStd.v6.0.7.0.G13034221027.hdf',
    'AIRS.2013.02.03.058.L2.RetStd.v6.0.7.0.G13034220513.hdf',
    'AIRS.2013.02.03.059.L2.RetStd.v6.0.7.0.G13034220427.hdf',
    'AIRS.2013.02.03.060.L2.RetStd.v6.0.7.0.G13034220449.hdf',
    'AIRS.2013.02.03.061.L2.RetStd.v6.0.7.0.G13034221859.hdf',
    'AIRS.2013.02.03.062.L2.RetStd.v6.0.7.0.G13034222002.hdf',
    'AIRS.2013.02.03.063.L2.RetStd.v6.0.7.0.G13034222206.hdf',
    'AIRS.2013.02.03.064.L2.RetStd.v6.0.7.0.G13034222153.hdf',
    'AIRS.2013.02.03.065.L2.RetStd.v6.0.7.0.G13034222218.hdf',
    'AIRS.2013.02.03.066.L2.RetStd.v6.0.7.0.G13034223743.hdf',
    'AIRS.2013.02.03.067.L2.RetStd.v6.0.7.0.G13034223732.hdf',
    'AIRS.2013.02.03.068.L2.RetStd.v6.0.7.0.G13034223710.hdf',
    'AIRS.2013.02.03.069.L2.RetStd.v6.0.7.0.G13034223453.hdf',
    'AIRS.2013.02.03.070.L2.RetStd.v6.0.7.0.G13034223633.hdf',
    'AIRS.2013.02.03.071.L2.RetStd.v6.0.7.0.G13034225337.hdf',
    'AIRS.2013.02.03.072.L2.RetStd.v6.0.7.0.G13034225143.hdf',
    'AIRS.2013.02.03.073.L2.RetStd.v6.0.7.0.G13034225203.hdf',
    'AIRS.2013.02.03.074.L2.RetStd.v6.0.7.0.G13034225204.hdf',
    'AIRS.2013.02.03.075.L2.RetStd.v6.0.7.0.G13034225055.hdf',
    'AIRS.2013.02.03.076.L2.RetStd.v6.0.7.0.G13034230532.hdf',
    'AIRS.2013.02.03.077.L2.RetStd.v6.0.7.0.G13034230503.hdf',
    'AIRS.2013.02.03.078.L2.RetStd.v6.0.7.0.G13034230457.hdf',
    'AIRS.2013.02.03.079.L2.RetStd.v6.0.7.0.G13034230435.hdf',
    'AIRS.2013.02.03.080.L2.RetStd.v6.0.7.0.G13034230619.hdf',
    'AIRS.2013.02.03.081.L2.RetStd.v6.0.7.0.G13034232228.hdf',
    'AIRS.2013.02.03.082.L2.RetStd.v6.0.7.0.G13034232139.hdf',
    'AIRS.2013.02.03.083.L2.RetStd.v6.0.7.0.G13034232228.hdf',
    'AIRS.2013.02.03.084.L2.RetStd.v6.0.7.0.G13034232154.hdf',
    'AIRS.2013.02.03.085.L2.RetStd.v6.0.7.0.G13034232055.hdf',
    'AIRS.2013.02.03.086.L2.RetStd.v6.0.7.0.G13034233243.hdf',
    'AIRS.2013.02.03.087.L2.RetStd.v6.0.7.0.G13034233738.hdf',
    'AIRS.2013.02.03.088.L2.RetStd.v6.0.7.0.G13034233859.hdf',
    'AIRS.2013.02.03.089.L2.RetStd.v6.0.7.0.G13034233735.hdf',
    'AIRS.2013.02.03.090.L2.RetStd.v6.0.7.0.G13034233705.hdf',
    'AIRS.2013.02.03.091.L2.RetStd.v6.0.7.0.G13034235126.hdf',
    'AIRS.2013.02.03.092.L2.RetStd.v6.0.7.0.G13034235143.hdf',
    'AIRS.2013.02.03.093.L2.RetStd.v6.0.7.0.G13034235246.hdf',
    'AIRS.2013.02.03.094.L2.RetStd.v6.0.7.0.G13034235119.hdf',
    'AIRS.2013.02.03.095.L2.RetStd.v6.0.7.0.G13034235130.hdf',
    'AIRS.2013.02.03.096.L2.RetStd.v6.0.7.0.G13035000454.hdf',
    'AIRS.2013.02.03.097.L2.RetStd.v6.0.7.0.G13035000750.hdf',
    'AIRS.2013.02.03.098.L2.RetStd.v6.0.7.0.G13035000657.hdf',
    'AIRS.2013.02.03.099.L2.RetStd.v6.0.7.0.G13035112041.hdf',
    'AIRS.2013.02.03.100.L2.RetStd.v6.0.7.0.G13035112132.hdf',
    'AIRS.2013.02.03.101.L2.RetStd.v6.0.7.0.G13035103022.hdf',
    'AIRS.2013.02.03.102.L2.RetStd.v6.0.7.0.G13035102232.hdf',
    'AIRS.2013.02.03.103.L2.RetStd.v6.0.7.0.G13035102346.hdf',
    'AIRS.2013.02.03.104.L2.RetStd.v6.0.7.0.G13035102743.hdf',
    'AIRS.2013.02.03.105.L2.RetStd.v6.0.7.0.G13035102913.hdf',
    'AIRS.2013.02.03.106.L2.RetStd.v6.0.7.0.G13035103744.hdf',
    'AIRS.2013.02.03.107.L2.RetStd.v6.0.7.0.G13035103758.hdf',
    'AIRS.2013.02.03.108.L2.RetStd.v6.0.7.0.G13035103857.hdf',
    'AIRS.2013.02.03.109.L2.RetStd.v6.0.7.0.G13035103746.hdf',
    'AIRS.2013.02.03.110.L2.RetStd.v6.0.7.0.G13035111837.hdf',
    'AIRS.2013.02.03.111.L2.RetStd.v6.0.7.0.G13035111752.hdf',
    'AIRS.2013.02.03.112.L2.RetStd.v6.0.7.0.G13035112138.hdf',
    'AIRS.2013.02.03.113.L2.RetStd.v6.0.7.0.G13035113607.hdf',
    'AIRS.2013.02.03.114.L2.RetStd.v6.0.7.0.G13035113502.hdf',
    'AIRS.2013.02.03.115.L2.RetStd.v6.0.7.0.G13035113530.hdf',
    'AIRS.2013.02.03.116.L2.RetStd.v6.0.7.0.G13035113624.hdf',
    'AIRS.2013.02.03.117.L2.RetStd.v6.0.7.0.G13035113629.hdf',
    'AIRS.2013.02.03.118.L2.RetStd.v6.0.7.0.G13035103512.hdf',
    'AIRS.2013.02.03.119.L2.RetStd.v6.0.7.0.G13035104728.hdf',
    'AIRS.2013.02.03.120.L2.RetStd.v6.0.7.0.G13035105132.hdf',
    'AIRS.2013.02.03.121.L2.RetStd.v6.0.7.0.G13035105023.hdf',
    'AIRS.2013.02.03.122.L2.RetStd.v6.0.7.0.G13035105017.hdf',
    'AIRS.2013.02.03.123.L2.RetStd.v6.0.7.0.G13035104927.hdf',
    'AIRS.2013.02.03.124.L2.RetStd.v6.0.7.0.G13035110538.hdf',
    'AIRS.2013.02.03.125.L2.RetStd.v6.0.7.0.G13035110503.hdf',
    'AIRS.2013.02.03.126.L2.RetStd.v6.0.7.0.G13035110420.hdf',
    'AIRS.2013.02.03.127.L2.RetStd.v6.0.7.0.G13035114815.hdf',
    'AIRS.2013.02.03.128.L2.RetStd.v6.0.7.0.G13035115024.hdf',
    'AIRS.2013.02.03.129.L2.RetStd.v6.0.7.0.G13035115048.hdf',
    'AIRS.2013.02.03.130.L2.RetStd.v6.0.7.0.G13035115105.hdf',
    'AIRS.2013.02.03.131.L2.RetStd.v6.0.7.0.G13035115013.hdf',
    'AIRS.2013.02.03.132.L2.RetStd.v6.0.7.0.G13035120515.hdf',
    'AIRS.2013.02.03.133.L2.RetStd.v6.0.7.0.G13035120538.hdf',
    'AIRS.2013.02.03.134.L2.RetStd.v6.0.7.0.G13035110358.hdf',
    'AIRS.2013.02.03.135.L2.RetStd.v6.0.7.0.G13035110046.hdf',
    'AIRS.2013.02.03.136.L2.RetStd.v6.0.7.0.G13035120546.hdf',
    'AIRS.2013.02.03.137.L2.RetStd.v6.0.7.0.G13035120615.hdf',
    'AIRS.2013.02.03.138.L2.RetStd.v6.0.7.0.G13035120556.hdf',
    'AIRS.2013.02.03.139.L2.RetStd.v6.0.7.0.G13035122104.hdf',
    'AIRS.2013.02.03.140.L2.RetStd.v6.0.7.0.G13035122020.hdf',
    'AIRS.2013.02.03.141.L2.RetStd.v6.0.7.0.G13035122153.hdf',
    'AIRS.2013.02.03.142.L2.RetStd.v6.0.7.0.G13035121926.hdf',
    'AIRS.2013.02.03.143.L2.RetStd.v6.0.7.0.G13035121712.hdf',
    'AIRS.2013.02.03.144.L2.RetStd.v6.0.7.0.G13035123415.hdf',
    'AIRS.2013.02.03.145.L2.RetStd.v6.0.7.0.G13035123630.hdf',
    'AIRS.2013.02.03.146.L2.RetStd.v6.0.7.0.G13035123656.hdf',
    'AIRS.2013.02.03.147.L2.RetStd.v6.0.7.0.G13035123554.hdf',
    'AIRS.2013.02.03.148.L2.RetStd.v6.0.7.0.G13035123536.hdf',
    'AIRS.2013.02.03.149.L2.RetStd.v6.0.7.0.G13035125102.hdf',
    'AIRS.2013.02.03.150.L2.RetStd.v6.0.7.0.G13035124955.hdf',
    'AIRS.2013.02.03.151.L2.RetStd.v6.0.7.0.G13035124550.hdf',
    'AIRS.2013.02.03.152.L2.RetStd.v6.0.7.0.G13035124834.hdf',
    'AIRS.2013.02.03.153.L2.RetStd.v6.0.7.0.G13035125119.hdf',
    'AIRS.2013.02.03.154.L2.RetStd.v6.0.7.0.G13035130558.hdf',
    'AIRS.2013.02.03.155.L2.RetStd.v6.0.7.0.G13035130553.hdf',
    'AIRS.2013.02.03.156.L2.RetStd.v6.0.7.0.G13035130607.hdf',
    'AIRS.2013.02.03.157.L2.RetStd.v6.0.7.0.G13035130616.hdf',
    'AIRS.2013.02.03.158.L2.RetStd.v6.0.7.0.G13035130600.hdf',
    'AIRS.2013.02.03.159.L2.RetStd.v6.0.7.0.G13035131815.hdf',
    'AIRS.2013.02.03.160.L2.RetStd.v6.0.7.0.G13035131740.hdf',
    'AIRS.2013.02.03.161.L2.RetStd.v6.0.7.0.G13035131940.hdf',
    'AIRS.2013.02.03.162.L2.RetStd.v6.0.7.0.G13035132004.hdf',
    'AIRS.2013.02.03.163.L2.RetStd.v6.0.7.0.G13035132019.hdf',
    'AIRS.2013.02.03.164.L2.RetStd.v6.0.7.0.G13035133538.hdf',
    'AIRS.2013.02.03.165.L2.RetStd.v6.0.7.0.G13035133426.hdf',
    'AIRS.2013.02.03.166.L2.RetStd.v6.0.7.0.G13035133653.hdf',
    'AIRS.2013.02.03.167.L2.RetStd.v6.0.7.0.G13035133214.hdf',
    'AIRS.2013.02.03.168.L2.RetStd.v6.0.7.0.G13035133202.hdf',
    'AIRS.2013.02.03.169.L2.RetStd.v6.0.7.0.G13035135225.hdf',
    'AIRS.2013.02.03.170.L2.RetStd.v6.0.7.0.G13035135156.hdf',
    'AIRS.2013.02.03.171.L2.RetStd.v6.0.7.0.G13035135133.hdf',
    'AIRS.2013.02.03.172.L2.RetStd.v6.0.7.0.G13035135108.hdf',
    'AIRS.2013.02.03.173.L2.RetStd.v6.0.7.0.G13035135136.hdf',
    'AIRS.2013.02.03.174.L2.RetStd.v6.0.7.0.G13035140501.hdf',
    'AIRS.2013.02.03.175.L2.RetStd.v6.0.7.0.G13035140353.hdf',
    'AIRS.2013.02.03.176.L2.RetStd.v6.0.7.0.G13035140242.hdf',
    'AIRS.2013.02.03.177.L2.RetStd.v6.0.7.0.G13035140242.hdf',
    'AIRS.2013.02.03.178.L2.RetStd.v6.0.7.0.G13035140253.hdf',
    'AIRS.2013.02.03.179.L2.RetStd.v6.0.7.0.G13035142006.hdf',
    'AIRS.2013.02.03.180.L2.RetStd.v6.0.7.0.G13035141911.hdf',
    'AIRS.2013.02.03.181.L2.RetStd.v6.0.7.0.G13035141948.hdf',
    'AIRS.2013.02.03.182.L2.RetStd.v6.0.7.0.G13035142041.hdf',
    'AIRS.2013.02.03.183.L2.RetStd.v6.0.7.0.G13035141904.hdf',
    'AIRS.2013.02.03.184.L2.RetStd.v6.0.7.0.G13035143058.hdf',
    'AIRS.2013.02.03.185.L2.RetStd.v6.0.7.0.G13035143433.hdf',
    'AIRS.2013.02.03.186.L2.RetStd.v6.0.7.0.G13035143558.hdf',
    'AIRS.2013.02.03.187.L2.RetStd.v6.0.7.0.G13035143559.hdf',
    'AIRS.2013.02.03.188.L2.RetStd.v6.0.7.0.G13035143503.hdf',
    'AIRS.2013.02.03.189.L2.RetStd.v6.0.7.0.G13035145056.hdf',
    'AIRS.2013.02.03.190.L2.RetStd.v6.0.7.0.G13035144914.hdf',
    'AIRS.2013.02.03.191.L2.RetStd.v6.0.7.0.G13035144812.hdf',
    'AIRS.2013.02.03.192.L2.RetStd.v6.0.7.0.G13035144757.hdf',
    'AIRS.2013.02.03.193.L2.RetStd.v6.0.7.0.G13035144651.hdf',
    'AIRS.2013.02.03.194.L2.RetStd.v6.0.7.0.G13035150232.hdf',
    'AIRS.2013.02.03.195.L2.RetStd.v6.0.7.0.G13035150144.hdf',
    'AIRS.2013.02.03.196.L2.RetStd.v6.0.7.0.G13035150450.hdf',
    'AIRS.2013.02.03.197.L2.RetStd.v6.0.7.0.G13035150452.hdf',
    'AIRS.2013.02.03.198.L2.RetStd.v6.0.7.0.G13035150507.hdf',
    'AIRS.2013.02.03.199.L2.RetStd.v6.0.7.0.G13035152116.hdf',
    'AIRS.2013.02.03.200.L2.RetStd.v6.0.7.0.G13035151738.hdf',
    'AIRS.2013.02.03.201.L2.RetStd.v6.0.7.0.G13035151810.hdf',
    'AIRS.2013.02.03.202.L2.RetStd.v6.0.7.0.G13035152105.hdf',
    'AIRS.2013.02.03.203.L2.RetStd.v6.0.7.0.G13035152038.hdf',
    'AIRS.2013.02.03.204.L2.RetStd.v6.0.7.0.G13035153618.hdf',
    'AIRS.2013.02.03.205.L2.RetStd.v6.0.7.0.G13035153601.hdf',
    'AIRS.2013.02.03.206.L2.RetStd.v6.0.7.0.G13035153519.hdf',
    'AIRS.2013.02.03.207.L2.RetStd.v6.0.7.0.G13035153330.hdf',
    'AIRS.2013.02.03.208.L2.RetStd.v6.0.7.0.G13035153314.hdf',
    'AIRS.2013.02.03.209.L2.RetStd.v6.0.7.0.G13035154723.hdf',
    'AIRS.2013.02.03.210.L2.RetStd.v6.0.7.0.G13035154810.hdf',
    'AIRS.2013.02.03.211.L2.RetStd.v6.0.7.0.G13035154749.hdf',
    'AIRS.2013.02.03.212.L2.RetStd.v6.0.7.0.G13035154937.hdf',
    'AIRS.2013.02.03.213.L2.RetStd.v6.0.7.0.G13035154955.hdf',
    'AIRS.2013.02.03.214.L2.RetStd.v6.0.7.0.G13035160455.hdf',
    'AIRS.2013.02.03.215.L2.RetStd.v6.0.7.0.G13035160552.hdf',
    'AIRS.2013.02.03.216.L2.RetStd.v6.0.7.0.G13035160505.hdf',
    'AIRS.2013.02.03.217.L2.RetStd.v6.0.7.0.G13035160116.hdf',
    'AIRS.2013.02.03.218.L2.RetStd.v6.0.7.0.G13035160454.hdf',
    'AIRS.2013.02.03.219.L2.RetStd.v6.0.7.0.G13035162103.hdf',
    'AIRS.2013.02.03.220.L2.RetStd.v6.0.7.0.G13035162051.hdf',
    'AIRS.2013.02.03.221.L2.RetStd.v6.0.7.0.G13035162055.hdf',
    'AIRS.2013.02.03.222.L2.RetStd.v6.0.7.0.G13035162109.hdf',
    'AIRS.2013.02.03.223.L2.RetStd.v6.0.7.0.G13035162212.hdf',
    'AIRS.2013.02.03.224.L2.RetStd.v6.0.7.0.G13035163525.hdf',
    'AIRS.2013.02.03.225.L2.RetStd.v6.0.7.0.G13035163317.hdf',
    'AIRS.2013.02.03.226.L2.RetStd.v6.0.7.0.G13035163319.hdf',
    'AIRS.2013.02.03.227.L2.RetStd.v6.0.7.0.G13035163345.hdf',
    'AIRS.2013.02.03.228.L2.RetStd.v6.0.7.0.G13035163338.hdf',
    'AIRS.2013.02.03.229.L2.RetStd.v6.0.7.0.G13035164906.hdf',
    'AIRS.2013.02.03.230.L2.RetStd.v6.0.7.0.G13035164927.hdf',
    'AIRS.2013.02.03.231.L2.RetStd.v6.0.7.0.G13035165044.hdf',
    'AIRS.2013.02.03.232.L2.RetStd.v6.0.7.0.G13035165137.hdf',
    'AIRS.2013.02.03.233.L2.RetStd.v6.0.7.0.G13035164818.hdf',
    'AIRS.2013.02.03.234.L2.RetStd.v6.0.7.0.G13035170348.hdf',
    'AIRS.2013.02.03.235.L2.RetStd.v6.0.7.0.G13035170639.hdf',
    'AIRS.2013.02.03.236.L2.RetStd.v6.0.7.0.G13035170632.hdf',
    'AIRS.2013.02.03.237.L2.RetStd.v6.0.7.0.G13035170611.hdf',
    'AIRS.2013.02.03.238.L2.RetStd.v6.0.7.0.G13035170538.hdf',
    'AIRS.2013.02.03.239.L2.RetStd.v6.0.7.0.G13035172128.hdf',
    'AIRS.2013.02.03.240.L2.RetStd.v6.0.7.0.G13035172103.hdf',
]

# time tolerance in seconds
time_tol = 300.

# distance tolerance in km
dist_tol = 12.

dap_filter = "^http://cvo.hysds.net:8080/opendap/.*\.hdf$"
url_prop = "urls"
dap_prop = "dap_urls"

for airs_file in airs_files:
    airs_dap_url = airs_dap_url_base + airs_file
    product_id = "index-airs.aqua_cloudsat-v%s-%s" % (app.config['MATCHUP_VERSION'],
                                                      os.path.basename(airs_dap_url)[5:19])
    os.system('/home/ops/verdi/ops/measures/scripts/generate_airs_cloudsat_matchup.sh %s' % airs_dap_url)
    if os.path.exists(product_id):
        os.system('scp -r %s puccini-ccmods:/data/public/staging/products/' % product_id)
        os.system('ssh puccini-ccmods "touch /data/public/staging/products/%s.done"' % product_id)
