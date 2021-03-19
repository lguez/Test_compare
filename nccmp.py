#!/usr/bin/env python3

import netCDF4
import sys
import argparse
import diff_funct

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--silent", action = "store_true")
args = parser.parse_args()
nc1 = netCDF4.Dataset(args.netCDF_file[0])
nc2 = netCDF4.Dataset(args.netCDF_file[1])
vars1 = nc1.variables.keys()
vars2 = nc2.variables.keys()
diff_found = False

for name in vars1 & vars2:
    diff_found = diff_funct.compare_vars(nc1.variables[name],
                                         nc2.variables[name],
                                         args.silent,
                                         tag = f"Variable {name}") or diff_found
    # (Note: call to compare_vars first to avoid short-circuit)
    
    if diff_found and args.silent: break

if diff_found: sys.exit(1)
