#!/usr/bin/env python
import argparse

from measures.lib.airs_mls import convert


if __name__ == "__main__":
   desc = "Convert AIRS-MLS matchup and joined MAT-files to NetCDF4 and add metadata."
   parser = argparse.ArgumentParser(description=desc)
   parser.add_argument('mat_file', help="input matchup MAT-file")
   parser.add_argument('joined_file', help="input joined MAT-file")
   parser.add_argument('nc4_file', help="output NetCDF4 file")
   args = parser.parse_args()
   convert(args.mat_file, args.joined_file, args.nc4_file)
