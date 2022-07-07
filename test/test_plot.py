#!/usr/bin/env python
import os, sys, logging
from pprint import pprint

from measures import app
from measures.lib.plot import plot_airs_cloudsat_matchup


logging.basicConfig(level=logging.DEBUG)


if __name__ == "__main__":
    matchup_file = sys.argv[1]
    plot_file = sys.argv[2]
    global_file = sys.argv[3]
    plot_airs_cloudsat_matchup(matchup_file, plot_file)
    plot_airs_cloudsat_matchup(matchup_file, global_file, map_global=True)
