#!/usr/bin/env python3

"""From nccmp_pism.py."""

import netCDF4
import numpy as np
import sys
import argparse

def compare_vars(v1, v2, silent = False, tag = None):
    """Return True if a difference if found."""
    
    if v1.shape != v2.shape:
        if not silent:
            if tag: print(tag, ":")
            print("Different shapes in the two files")
            print("-------------\n")

        diff_found = True
    else:
        if v1.size == 0:
            if not silent:
                if tag: print(tag, ":")
                print('0 size')
                print("-------------\n")
                
            diff_found = False
        else:
            if np.any(v1[:] != v2[:]):
                if not silent:
                    if tag: print(tag, ":")
                    print("Different content")
                    print("-------------\n")
                    
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
    diff_found = compare_vars(nc1.variables[name], nc2.variables[name],
                              args.silent, tag = f"Variable {name}") \
                              or diff_found
    # (Note: call to compare_vars first to avoid short-circuit)
    
    if diff_found and args.silent: break

if diff_found: sys.exit(1)
