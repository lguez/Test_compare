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

        difference_found = True
    else:
        if var1.size == 0:
            if not args.silent: print(f'Variable {name}: 0 size.')
            difference_found = False
        else:
            if np.any(var1[:] != var2[:]):
                if not args.silent: print(f"Variable {name}, different content")
                difference_found = True
            else:
                difference_found = False

    return difference_found

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--silent", action="store_true")
args = parser.parse_args()
nc1 = netCDF4.Dataset(args.netCDF_file[0])
nc2 = netCDF4.Dataset(args.netCDF_file[1])
vars1 = nc1.variables.keys()
vars2 = nc2.variables.keys()
any_difference = False

for name in vars1 & vars2:
    difference_found = compare_vars(nc1, nc2, name)
    any_difference = any_difference or difference_found
    if difference_found and args.silent: break

if any_difference: sys.exit(1)
