from setuptools import setup, find_packages
from Cython.Build import cythonize
import numpy
import os, sys
sys.path.append('test')


setup ( name = 'measures',
        version = '0.1.0',
        description = 'MEaSUREs Package',
        author = 'Gerald Manipon',
        author_email = 'Geraldjohn.M.Manipon@jpl.nasa.gov',
        packages = find_packages(),
        ext_modules = cythonize("measures/lib/fast_utils.pyx"),
        include_dirs = [ numpy.get_include() ],
        #scripts = scripts,
        test_suite = "runAllTests.getAllTestsTestSuite",
        dependency_links = ['http://github.com/pymonger/pydap/tarball/master#egg=pydap-3.1.1'],
        install_requires=[
            'pydap==3.1.1', 'flask>=1.0.0', 'prov_es==0.1.1'
        ]
)
