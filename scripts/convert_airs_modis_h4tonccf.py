#!/usr/bin/env python
import argparse

from measures.lib.airs_modis import convert


if __name__ == "__main__":
   desc = "Convert AIRS-MODIS matchup HDF4 file to NetCDF4 and add metadata."
   parser = argparse.ArgumentParser(description=desc)
   parser.add_argument('h4_file', help="input HDF4 file")
   parser.add_argument('nc4_file', help="output NetCDF4 file")
   args = parser.parse_args()
   convert(args.h4_file, args.nc4_file) 
