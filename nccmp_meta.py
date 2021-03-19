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
diff_found = diff_funct.diff_dict(f1.__dict__, f2.__dict__, args.silent,
                                  tag = "All attributes of the dataset")
if args.silent and diff_found: sys.exit(1)

for tag, v1, v2 in [("Data_model", f1.data_model, f2.data_model),
                    ("Disk_format", f1.disk_format, f2.disk_format),
                    ("File_format", f1.file_format, f2.file_format),
                    ("Dimension names", f1.dimensions.keys(),
                     f2.dimensions.keys()), ("Variable names", vars1, vars2)]:
    diff_found = diff_funct.cmp(v1, v2, args.silent, tag) or diff_found
    if diff_found and args.silent: sys.exit(1)

for x in f1.dimensions:
    if x in f2.dimensions:
        diff_found = diff_funct.cmp(len(f1.dimensions[x]),
                                    len(f2.dimensions[x]), args.silent,
                                    tag = f"Size of dimension {x}") \
                                    or diff_found
        if diff_found and args.silent: sys.exit(1)
        
for x in vars1 & vars2:
        diff_found = diff_funct.diff_dict(f1[x].__dict__, f2[x].__dict__,
                                          args.silent,
                                          tag = f"Attributes of variable {x}") \
                                          or diff_found
        if args.silent and diff_found: sys.exit(1)

        for attribute in ["dtype", "dimensions", "shape"]:
            diff_found = \
                diff_funct.cmp(f1[x].__getattribute__(attribute), 
                               f2[x].__getattribute__(attribute), args.silent, \
                               tag = f"{attribute} of variable {x}") \
                               or diff_found
            if diff_found and args.silent: sys.exit(1)
