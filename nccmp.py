#!/usr/bin/env python3

import netCDF4
import sys
import argparse
import diff_funct

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--silent", action = "store_true")
args = parser.parse_args()

f1 = netCDF4.Dataset(args.netCDF_file[0])
f2 = netCDF4.Dataset(args.netCDF_file[1])

vars1 = f1.variables.keys()
vars2 = f2.variables.keys()
diff_found = False

for x in vars1 & vars2:
    diff_found = diff_funct.compare_vars(f1.variables[x], f2.variables[x],
                                         args.silent, tag = f"Variable {x}") \
                                         or diff_found
    # (Note: call to compare_vars first to avoid short-circuit)
    
    if diff_found and args.silent: break

if diff_found: sys.exit(1)
