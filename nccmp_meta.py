#!/usr/bin/env python3

import netCDF4
import sys
import argparse
import jumble

def cmp(tag, v1, v2):
    diff_found = v1 != v2
    
    if diff_found and not args.silent:
        print(tag, ":\n")
        print(v1)
        print()
        print(v2)
        print("-------------\n")

    return diff_found

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--silent", action="store_true")
args = parser.parse_args()

f1 = netCDF4.Dataset(args.netCDF_file[0])
f2 = netCDF4.Dataset(args.netCDF_file[1])

diff_found = jumble.diff_dict(f1.__dict__, f2.__dict__, args.silent,
                              tag = "All attributes of the dataset")
if args.silent and diff_found: sys.exit(1)

for tag, v1, v2 in [("Data_model", f1.data_model, f2.data_model),
                    ("Disk_format", f1.disk_format, f2.disk_format),
                    ("File_format", f1.file_format, f2.file_format),
                    ("Dimension names", f1.dimensions.keys(),
                     f2.dimensions.keys()),
                    ("Variable names", f1.variables.keys(),
                     f2.variables.keys())]:
    diff_found = cmp(tag, v1, v2) or diff_found
    if diff_found and args.silent: sys.exit(1)

for x in f1.dimensions:
    if x in f2.dimensions:
        diff_found = cmp(f"Size of dimension {x}", len(f1.dimensions[x]),
                         len(f2.dimensions[x])) or diff_found
        if diff_found and args.silent: sys.exit(1)
        
for x in f1.variables:
    if x in f2.variables:
        diff_found = jumble.diff_dict(f1.variables[x].__dict__,
                                      f2.variables[x].__dict__, args.silent,
                                      tag = f"Attributes of variable {x}") \
                                      or diff_found
        if args.silent and diff_found: sys.exit(1)

        for attribute in ["dtype", "dimensions", "shape"]:
            diff_found = cmp(f"{attribute} of variable {x}",
                             f1.variables[x].__getattribute__(attribute), 
                             f2.variables[x].__getattribute__(attribute)) \
                             or diff_found
            if diff_found and args.silent: sys.exit(1)
