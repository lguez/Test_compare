#!/usr/bin/env python3

"""From nccmp_pism.py."""

import netCDF4
import numpy as np
import sys
import argparse

def compare_vars(nc1, nc2, name):
    """Return True if a difference if found. name must be a variable
    common to nc1 and nc2."""
    
    var1 = nc1.variables[name]
    var2 = nc2.variables[name]

    if var1.shape != var2.shape:
        if not args.silent:
            print(f"Variable {name}, different shapes in the two files")

        diff_found = True
    else:
        if var1.size == 0:
            if not args.silent: print(f'Variable {name}: 0 size.')
            diff_found = False
        else:
            if np.any(var1[:] != var2[:]):
                if not args.silent: print(f"Variable {name}, different content")
                diff_found = True
            else:
                diff_found = False

    return diff_found

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--silent", action="store_true")
args = parser.parse_args()
nc1 = netCDF4.Dataset(args.netCDF_file[0])
nc2 = netCDF4.Dataset(args.netCDF_file[1])
vars1 = nc1.variables.keys()
vars2 = nc2.variables.keys()
diff_found = False

for name in vars1 & vars2:
    diff_found = compare_vars(nc1, nc2, name) or diff_found
    # (Note: call to compare_vars first to avoid short-circuit)
    
    if diff_found and args.silent: break

if diff_found: sys.exit(1)
