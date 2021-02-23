#!/usr/bin/env python3

import netCDF4
import sys
import argparse
import jumble

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--silent", action="store_true")
args = parser.parse_args()
n_diff = 0

def cmp(tag, v1, v2):
    if v1 != v2:
        if args.silent:
            sys.exit(1)
        else:
            print(tag, ":\n")
            print(v1)
            print()
            print(v2)
            print("-------------\n")
            return 1
    else:
        return 0

f1 = netCDF4.Dataset(args.netCDF_file[0])
f2 = netCDF4.Dataset(args.netCDF_file[1])

n_diff += jumble.diff_dict(f1.__dict__, f2.__dict__, args.silent,
                           tag = "All attributes of the dataset")
if args.silent and n_diff != 0: sys.exit(1)
n_diff += cmp("Data_model", f1.data_model, f2.data_model)
n_diff += cmp("Disk_format", f1.disk_format, f2.disk_format)
n_diff += cmp("File_format", f1.file_format, f2.file_format)
n_diff += cmp("Dimension names", f1.dimensions.keys(), f2.dimensions.keys())
for x in f1.dimensions:
    n_diff += cmp(f"Size of dimension {x}", len(f1.dimensions[x]),
                  len(f2.dimensions[x]))
n_diff += cmp("Variable names", f1.variables.keys(), f2.variables.keys())

for x in f1.variables:
    n_diff += jumble.diff_dict(f1.variables[x].__dict__,
                               f2.variables[x].__dict__, args.silent,
                               tag = f"Attributes of variable {x}")
    if args.silent and n_diff != 0: sys.exit(1)

    for attribute in ["dtype", "dimensions", "shape"]:
        n_diff += cmp(f"{attribute} of variable {x}",
                      f1.variables[x].__getattribute__(attribute), 
                      f2.variables[x].__getattribute__(attribute))

if n_diff != 0: sys.exit(1)
