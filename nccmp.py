#!/usr/bin/env python3

"""Requires Python >= 3.6."""

import netCDF4
import compare_util

def nccmp(old, new, silent = False, data_only = False):
    f1 = netCDF4.Dataset(old)
    f2 = netCDF4.Dataset(new)

    vars1 = f1.variables.keys()
    vars2 = f2.variables.keys()

    if data_only:
        diff_found = False
    else:
        diff_found = compare_util.diff_dict(f1.__dict__, f2.__dict__, silent,
                                            tag = "All attributes of the "
                                            "dataset")
        if not silent or not diff_found:
            for tag, v1, v2 in [("Data_model", f1.data_model, f2.data_model),
                                ("Disk_format", f1.disk_format, f2.disk_format),
                                ("File_format", f1.file_format, f2.file_format),
                                ("Dimension names", f1.dimensions.keys(),
                                 f2.dimensions.keys()),
                                ("Variable names", vars1, vars2)]:
                diff_found = compare_util.cmp(v1, v2, silent, tag) or diff_found
                if diff_found and silent: break

        if not silent or not diff_found:
            for x in f1.dimensions:
                if x in f2.dimensions:
                    diff_found = compare_util.cmp(len(f1.dimensions[x]),
                                                  len(f2.dimensions[x]), silent,
                                                  tag = "Size of dimension "
                                                  f"{x}") or diff_found
                    if diff_found and silent: break

        inters_vars = vars1 & vars2

        while len(inters_vars) != 0 and (not silent or not diff_found):
            x = inters_vars.pop()
            diff_found \
                = compare_util.diff_dict(f1[x].__dict__, f2[x].__dict__,
                                         silent, tag = "Attributes of "
                                         f"variable {x}") or diff_found

            if not silent or not diff_found:
                for attribute in ["dtype", "dimensions", "shape"]:
                    diff_found = \
                        compare_util.cmp(f1[x].__getattribute__(attribute), 
                                         f2[x].__getattribute__(attribute),
                                         silent, \
                                         tag = f"{attribute} of variable {x}") \
                            or diff_found
                    if diff_found and silent: break

    if not silent or not diff_found:
        for x in vars1 & vars2:
            diff_found = compare_util.compare_vars(f1[x], f2[x], silent,
                                                   tag = f"Variable {x}") \
                                                   or diff_found
            # (Note: call to compare_vars first to avoid short-circuit)

            if diff_found and silent: break

    if diff_found:
        return 1
    else:
        return 0

if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser()
    parser.add_argument("netCDF_file", nargs = 2)
    parser.add_argument("-s", "--silent", action = "store_true")
    parser.add_argument("-d", "--data-only", action = "store_true",
                        help = "compare only data")
    args = parser.parse_args()

    nccmp_return = nccmp(*args.netCDF_file, args.silent, args.data_only)
    sys.exit(nccmp_return)
