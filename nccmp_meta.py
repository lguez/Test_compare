#!/usr/bin/env python3

import netCDF4
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("netCDF_file", nargs = 2)
parser.add_argument("--silent", action="store_true")
args = parser.parse_args()

def cmp(v1, v2):
    if v1 != v2:
        if not args.silent:
            print(v1)
            print(v2)
            
        sys.exit(1)

f1 = netCDF4.Dataset(args.netCDF_file[0])
f2 = netCDF4.Dataset(args.netCDF_file[1])
cmp(f1.__dict__, f2.__dict__)
cmp(f1.data_model, f2.data_model)
cmp(f1.disk_format, f2.disk_format)
cmp(f1.file_format, f2.file_format)
cmp(f1.dimensions.keys(), f2.dimensions.keys())
for x in f1.dimensions: cmp(len(f1.dimensions[x]), len(f2.dimensions[x]))
cmp(f1.variables.keys(), f2.variables.keys())

for x in f1.variables:
    for attribute in ["__dict__", "dtype", "dimensions", "shape"]:
        cmp(f1.variables[x].__getattribute__(attribute), 
            f2.variables[x].__getattribute__(attribute))
