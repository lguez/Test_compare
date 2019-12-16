#!/usr/bin/env python3

from sys import argv, exit
from getopt import getopt, GetoptError

## @package nccmp
## Compares NetCDF files by absolute max norms of difference of variables
##
## Without options,
## \code
## nccmp.py foo.nc bar.nc
## \endcode 
## compares all the variables in \c foo.nc and \c bar.nc.
## 
## Option \c -v allows selecting varibles to compare:
## \code
## nccmp.py -v thk,cbar foo.nc bar.nc
## \endcode
## only compares \c thk and \c cbar.
## 
## Option \c -t sets the tolerance:
## \code
## nccmp.py -t 1e-6 foo.nc bar.nc
## \endcode
## compares all the variables using the tolerance of 1e-6.
## 
## Finally, option \c -x \b excludes variables given with \c -v, instead of
## selecting them for comparison.
## 
## Run with --help to get a "usage" message.

tol = 0.0   # default tolerance is perfection

def success(relative):
    if relative:
        print("Common variables are the same within relative tolerance %.1e" 
              % tol)
    else:        
        print("Common variables are the same within tolerance %.1e" % tol)
    exit(0)

def failure():
    print("Files are different.")
    exit(1)

usage="""
nccmp.py compares NetCDF files by absolute max norms of difference of variables
usage:
  nccmp.py foo.nc bar.nc            compare all variables
  nccmp.py -v A,B foo.nc bar.nc     compare variables A and B
  nccmp.py -x -v C foo.nc bar.nc    compare all variables except C
  nccmp.py -t 1e-6 foo.nc bar.nc    use tolerance 1e-6 instead of default of 0
"""

def usagefailure(message):
    print(message)
    print()
    print(usage)
    exit(2)

def compare_vars(nc1, nc2, name, tol, relative=False):
    from numpy import squeeze, isnan, ma

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

    try:
        mask = var1.mask | var2.mask
    except:
        usagefailure("ERROR: VARIABLE '%s' OF INCOMPATIBLE SHAPES (?) IN FILES"
                     % name)

    if mask.all():
        print('Variable %10s: no values to compare.' % name)
        return

    var1 = ma.array(var1, mask = mask)
    var2 = ma.array(var2, mask = mask)

    delta = abs(var1 - var2).max()

    if relative:
        denom = max(abs(var1).max(), abs(var2).max())
        if denom > 0:
            delta = delta / denom

    # The actual check:
    if (delta > tol):
        print("name = %s, delta = %e, tol = %e" % (name, delta, tol))
        failure()


def compare(file1, file2, variables, exclude, tol, relative):
    try:
        from netCDF4 import Dataset
    except:
        print("nccmp_pism.py: netCDF4 is not installed!")
        exit(2)

    from numpy import unique, r_

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
    from numpy import double
    try:
      opts, args = getopt(argv[1:], "t:v:xr", ["help","usage"])
    except GetoptError:
      usagefailure('ERROR: INCORRECT COMMAND LINE ARGUMENTS FOR nccmp.py')
    file1 = ""
    file2 = ""
    variables = []
    exclude = False
    relative = False
    for (opt, arg) in opts:
        if opt == "-t":
            tol = double(arg)
        if opt == "-x":
            exclude = True
        if opt == "-r":
            relative = True
        if opt == "-v":
            variables = arg.split(",")
        if opt in ("--help", "--usage"):
            print(usage)
            exit(0)

    if len(args) != 2:
        usagefailure('ERROR: WRONG NUMBER OF ARGUMENTS FOR nccmp.py')

    compare(args[0],args[1], variables, exclude, tol, relative)
    success(relative)
