#!/usr/bin/env python3

"""From nccmp_pism.py."""

import netCDF4
import numpy as np
import sys
import argparse

def compare_vars(nc1, nc2, name):
    """Return True if a difference if found."""
    
    try:
        var1 = nc1.variables[name]
    except:
        if not args.silent: print(f"Variable {name} not found in file 1")
        return True

    try:
        var2 = nc2.variables[name]
    except:
        if not args.silent: print(f"Variable {name} not found in file 2")
        return True

    if var1.shape != var2.shape:
        if not args.silent:
            print(f"Variable {name}, different shapes in the two files")
            
        return True

    if var1.size == 0:
        if not args.silent: print(f'Variable {name}: 0 size.')
        return False
    else:
        if np.any(var1[:] != var2[:]):
            if not args.silent: print(f"Variable {name}, different content")
            return True
        else:
            return False

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--brief", action="store_true")
parser.add_argument("--silent", action="store_true")
args = parser.parse_args()
nc1 = netCDF4.Dataset(args.netCDF_file[0])
nc2 = netCDF4.Dataset(args.netCDF_file[1])
vars1 = list(nc1.variables.keys())
vars2 = list(nc2.variables.keys())
variables = np.unique(vars1 +  vars2)
any_difference = False

for name in variables:
    difference_found = compare_vars(nc1, nc2, name)
    any_difference = any_difference or difference_found
    if difference_found and args.brief: break

if any_difference: sys.exit(1)
