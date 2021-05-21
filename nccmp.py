#!/usr/bin/env python3

import netCDF4
import sys
import argparse
import util

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("-s", "--silent", action = "store_true")
parser.add_argument("-d", "--data", action = "store_true",
                    help = "compare only data")
args = parser.parse_args()

f1 = netCDF4.Dataset(args.netCDF_file[0])
f2 = netCDF4.Dataset(args.netCDF_file[1])

vars1 = f1.variables.keys()
vars2 = f2.variables.keys()

if args.data:
    diff_found = False
else:
    diff_found = util.diff_dict(f1.__dict__, f2.__dict__, args.silent,
                                      tag = "All attributes of the dataset")
    if args.silent and diff_found: sys.exit(1)

    for tag, v1, v2 in [("Data_model", f1.data_model, f2.data_model),
                        ("Disk_format", f1.disk_format, f2.disk_format),
                        ("File_format", f1.file_format, f2.file_format),
                        ("Dimension names", f1.dimensions.keys(),
                         f2.dimensions.keys()), ("Variable names", vars1,
                                                 vars2)]:
        diff_found = util.cmp(v1, v2, args.silent, tag) or diff_found
        if diff_found and args.silent: sys.exit(1)

    for x in f1.dimensions:
        if x in f2.dimensions:
            diff_found = util.cmp(len(f1.dimensions[x]),
                                        len(f2.dimensions[x]), args.silent,
                                        tag = f"Size of dimension {x}") \
                                        or diff_found
            if diff_found and args.silent: sys.exit(1)

    for x in vars1 & vars2:
            diff_found \
                = util.diff_dict(f1[x].__dict__, f2[x].__dict__,
                                       args.silent,
                                       tag = f"Attributes of variable {x}") \
                                       or diff_found
            if args.silent and diff_found: sys.exit(1)

            for attribute in ["dtype", "dimensions", "shape"]:
                diff_found = \
                    util.cmp(f1[x].__getattribute__(attribute), 
                                   f2[x].__getattribute__(attribute),
                                   args.silent, \
                                   tag = f"{attribute} of variable {x}") \
                                   or diff_found
                if diff_found and args.silent: sys.exit(1)

for x in vars1 & vars2:
    diff_found = util.compare_vars(f1[x], f2[x], args.silent,
                                         tag = f"Variable {x}") or diff_found
    # (Note: call to compare_vars first to avoid short-circuit)
    
    if diff_found and args.silent: break

if diff_found: sys.exit(1)
