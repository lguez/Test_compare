#!/usr/bin/env python3

"""Requires Python >= 3.6."""

import netCDF4
import compare_util
from os import path

def nccmp(f1, f2, silent = False, data_only = False):
    """f1 and f2 can be either filenames or open file objects."""

    if isinstance(f1, str):
        file_1 = netCDF4.Dataset(f1)
        file_2 = netCDF4.Dataset(f2)
    else:
        # nccmp may call itself with file object arguments.
        file_1 = f1
        file_2 = f2

    vars1 = file_1.variables.keys()
    vars2 = file_2.variables.keys()

    if data_only:
        diff_found = False
    else:
        tag = "All attributes of the dataset"
        diff_found = compare_util.diff_dict(file_1.__dict__, file_2.__dict__,
                                            silent, tag)
        groups1 = file_1.groups.keys()
        groups2 = file_2.groups.keys()

        if not silent or not diff_found:
            for tag, v1, v2 in [("Data_model", file_1.data_model,
                                 file_2.data_model),
                                ("Disk_format", file_1.disk_format,
                                 file_2.disk_format),
                                ("File_format", file_1.file_format,
                                 file_2.file_format),
                                ("Dimension names", file_1.dimensions.keys(),
                                 file_2.dimensions.keys()),
                                ("Variable names", vars1, vars2),
                                ("Group names", groups1, groups2)]:
                diff_found = compare_util.cmp(v1, v2, silent, tag) or diff_found
                if diff_found and silent: break

        if not silent or not diff_found:
            for x in file_1.dimensions:
                if x in file_2.dimensions:
                    tag = f"Size of dimension {x}"
                    diff_found \
                        = compare_util.cmp(len(file_1.dimensions[x]),
                                           len(file_2.dimensions[x]), silent,
                                           tag) or diff_found
                    if diff_found and silent: break

        inters_vars = vars1 & vars2

        while len(inters_vars) != 0 and (not silent or not diff_found):
            x = inters_vars.pop()
            tag = f"Attributes of variable {file_1.path}/{x}"
            diff_found \
                = compare_util.diff_dict(file_1[x].__dict__, file_2[x].__dict__,
                                         silent, tag) or diff_found

            if not silent or not diff_found:
                for attribute in ["dtype", "dimensions", "shape"]:
                    tag = f"{attribute} of variable {file_1.path}/{x}"
                    diff_found = \
                        compare_util.cmp(file_1[x].__getattribute__(attribute),
                                         file_2[x].__getattribute__(attribute),
                                         silent, tag) or diff_found
                    if diff_found and silent: break

        inters_groups = groups1 & groups2

        while len(inters_groups) != 0 and (not silent or not diff_found):
            x = inters_groups.pop()
            diff_found = nccmp(file_1[x], file_2[x], silent, data_only) == 1 \
                or diff_found

    if not silent or not diff_found:
        for x in vars1 & vars2:
            tag = f"Variable {path.join(file_1.path, x)}"
            diff_found \
                = compare_util.compare_vars(file_1[x], file_2[x], silent, tag) \
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
