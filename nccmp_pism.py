#!/usr/bin/env python3

import sys
from netCDF4 import Dataset
from numpy import unique, r_, squeeze, isnan, ma

def success(relative):
    if relative:
        print("Common variables are the same within relative tolerance %.1e" 
              % tol)
    else:        
        print("Common variables are the same within tolerance %.1e" % tol)
    sys.exit(0)

def failure():
    print("Files are different.")
    sys.exit(1)

def usagefailure(message):
    print(message)
    print()
    sys.exit(2)

def compare_vars(nc1, nc2, name, tol, relative):
    try:
        var1 = ma.array(squeeze(nc1.variables[name][:]))
    except:
        print("VARIABLE '%s' NOT FOUND IN FILE 1" % name)
        return
    try:
        var2 = ma.array(squeeze(nc2.variables[name][:]))
    except:
        print("ERROR: VARIABLE '%s' NOT FOUND IN FILE 2" % name)
        return

    if var1.shape != var2.shape:
        usagefailure(f"Error: variable {name}, incompatible shapes in files")

    if var1.size == 0:
        print(f'Variable {name}: 0 size.')
    else:        
        mask = var1.mask | var2.mask

        if mask.all():
            print(f'Variable {name}: domains of definition do not intersect.')
        else:
            var1 = ma.array(var1, mask = mask)
            var2 = ma.array(var2, mask = mask)

            delta = abs(var1 - var2).max()

            if relative:
                denom = max(abs(var1).max(), abs(var2).max())
                if denom > 0:
                    delta = delta / denom

            # The actual check:
            if (delta > tol):
                print(f"name = {name}, delta = {delta}")

def compare(file1, file2, variables, exclude, tol, relative):
    try:
        nc1 = Dataset(file1, 'r')
    except:
        usagefailure("ERROR: FILE '%s' CANNOT BE OPENED FOR READING" % file1)
    try:
        nc2 = Dataset(file2, 'r')
    except:
        usagefailure("ERROR: FILE '%s' CANNOT BE OPENED FOR READING" % file2)

    if (exclude == False):
        if len(variables) == 0:
            vars1 = list(nc1.variables.keys())
            vars2 = list(nc2.variables.keys())
            variables = unique(r_[vars1, vars2])

        for each in variables:
            compare_vars(nc1, nc2, each, tol, relative)
    else:
        vars1 = nc1.variables.keys()
        vars2 = nc2.variables.keys()
        vars = unique(r_[vars1, vars2])

        for each in vars:
            if (each in variables):
                continue
            compare_vars(nc1, nc2, each, tol, relative)

if __name__ == "__main__":
    import argparse

    description = \
    """Compares NetCDF variables by infinite norm."""

    parser = argparse.ArgumentParser(description = description)
    parser.add_argument("file1")
    parser.add_argument("file2")
    parser.add_argument("--tol", "-t", help = "tolerance (default 0)",
                        type = float, default = 0.)
    parser.add_argument("--relative", "-r",
                        help =
                        "compare relative difference instead of absolute",
                        action = "store_true")
    parser.add_argument("--variables", "-v",
                        help = "variables to compare (default all) or to "
                        "exclude if -x")
    parser.add_argument("--exclude", "-x", help = "exclude mode",
                        action = "store_true")
    args = parser.parse_args()
    
    if args.variables:
        variables = args.variables.split(",")
    else:
        variables = []

    compare(args.file1,args.file2, variables, args.exclude, args.tol,
            args.relative)
    ##success(relative)
