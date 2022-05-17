#!/usr/bin/env python3

"""Requires Python >= 3.6."""

import netCDF4
import compare_util

def nccmp(f1, f2, silent = False, data_only = False):
    if isinstance(f1, str):
        f1 = netCDF4.Dataset(f1)
        f2 = netCDF4.Dataset(f2)

    vars1 = f1.variables.keys()
    vars2 = f2.variables.keys()

    if data_only:
        diff_found = False
    else:
        diff_found = compare_util.diff_dict(f1.__dict__, f2.__dict__, silent,
                                            tag = "All attributes of the "
                                            "dataset")
        groups1 = f1.groups.keys()
        groups2 = f2.groups.keys()

        if not silent or not diff_found:
            for tag, v1, v2 in [("Data_model", f1.data_model, f2.data_model),
                                ("Disk_format", f1.disk_format, f2.disk_format),
                                ("File_format", f1.file_format, f2.file_format),
                                ("Dimension names", f1.dimensions.keys(),
                                 f2.dimensions.keys()),
                                ("Variable names", vars1, vars2),
                                ("Group names", groups1, groups2)]:
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
            tag = f"Attributes of variable {f1.path}/{x}"
            diff_found \
                = compare_util.diff_dict(f1[x].__dict__, f2[x].__dict__,
                                         silent, tag) or diff_found

            if not silent or not diff_found:
                for attribute in ["dtype", "dimensions", "shape"]:
                    tag = f"{attribute} of variable {f1.path}/{x}"
                    diff_found = \
                        compare_util.cmp(f1[x].__getattribute__(attribute), 
                                         f2[x].__getattribute__(attribute),
                                         silent, tag) or diff_found
                    if diff_found and silent: break

        inters_groups = groups1 & groups2

        while len(inters_groups) != 0 and (not silent or not diff_found):
            x = inters_groups.pop()
            diff_found = nccmp(f1[x], f2[x], silent, data_only) == 1 \
                or diff_found

    if not silent or not diff_found:
        for x in vars1 & vars2:
            tag = f"Variable {f1.path}/{x}"
            diff_found = compare_util.compare_vars(f1[x], f2[x], silent, tag) \
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
