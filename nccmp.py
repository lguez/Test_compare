#!/usr/bin/env python3

"""Requires Python >= 3.6."""

import sys
from os import path
import io

import netCDF4

import compare_util

def nccmp(
    f1, f2, silent=False, data_only=False, detail_file=sys.stdout, ign_att=None
):
    """f1 and f2 can be either filenames or open file objects. ign_att may
    be a list of global attributes.

    """

    if isinstance(f1, str):
        file_1 = netCDF4.Dataset(f1)
        file_2 = netCDF4.Dataset(f2)
    else:
        # nccmp may call itself with file object arguments.
        file_1 = f1
        file_2 = f2

    # We need to insert a header before detailed diagnostic, but only
    # if we find differences, so create a new text stream:
    detail_subfile = io.StringIO()

    vars1 = file_1.variables.keys()
    vars2 = file_2.variables.keys()
    groups1 = file_1.groups.keys()
    groups2 = file_2.groups.keys()

    if data_only:
        diff_found = False
    else:
        # Compare metadata:

        tag = "All attributes of the dataset"

        if ign_att is None:
            dict_1 = file_1.__dict__
            dict_2 = file_2.__dict__
        else:
            dict_1 = file_1.__dict__.copy()
            dict_2 = file_2.__dict__.copy()

            for attribute in ign_att:
                try:
                    del dict_1[attribute]
                    del dict_2[attribute]
                except KeyError:
                    pass

        diff_found = compare_util.diff_dict(
            dict_1, dict_2, silent, tag, detail_subfile
        )

        if not silent or not diff_found:
            for tag, v1, v2 in [
                ("Data_model", file_1.data_model, file_2.data_model),
                ("Disk_format", file_1.disk_format, file_2.disk_format),
                ("File_format", file_1.file_format, file_2.file_format),
                (
                    "Dimension names",
                    set(file_1.dimensions.keys()),
                    set(file_2.dimensions.keys()),
                ),
                ("Variable names", set(vars1), set(vars2)),
                ("Group names", set(groups1), set(groups2)),
            ]:
                diff_found = (
                    compare_util.cmp(v1, v2, silent, tag, detail_subfile)
                    or diff_found
                )
                if diff_found and silent:
                    break

        if not silent or not diff_found:
            for x in file_1.dimensions:
                if x in file_2.dimensions:
                    tag = f"Size of dimension {x}"
                    diff_found = (
                        compare_util.cmp(
                            len(file_1.dimensions[x]),
                            len(file_2.dimensions[x]),
                            silent,
                            tag,
                            detail_subfile,
                        )
                        or diff_found
                    )
                    if diff_found and silent:
                        break

        inters_vars = vars1 & vars2

        while len(inters_vars) != 0 and (not silent or not diff_found):
            x = inters_vars.pop()
            tag = f"Attributes of variable {path.join(file_1.path, x)}"

            # filters may return None so catch the exception:

            try:
                dict_1 = file_1[x].__dict__ | file_1[x].filters()
            except TypeError:
                dict_1 = file_1[x].__dict__

            try:
                dict_2 = file_2[x].__dict__ | file_2[x].filters()
            except TypeError:
                dict_2 = file_2[x].__dict__

            diff_found = (
                compare_util.diff_dict(
                    dict_1, dict_2, silent, tag, detail_subfile
                )
                or diff_found
            )

            if not silent or not diff_found:
                for attribute in ["dtype", "dimensions", "shape"]:
                    tag = f"{attribute} of variable {path.join(file_1.path, x)}"
                    diff_found = (
                        compare_util.cmp(
                            file_1[x].__getattribute__(attribute),
                            file_2[x].__getattribute__(attribute),
                            silent,
                            tag,
                            detail_subfile,
                        )
                        or diff_found
                    )
                    if diff_found and silent:
                        break

    if not silent or not diff_found:
        # Compare the data part:
        # Note that we cannot reuse inters_vars, which has been emptied.

        for x in vars1 & vars2:
            tag = f"Variable {path.join(file_1.path, x)}"
            diff_found = (
                compare_util.cmp_ndarr(
                    file_1[x], file_2[x], silent, tag, detail_subfile
                )
                or diff_found
            )
            # (Note: call to cmp_ndarr first to avoid short-circuit)

            if diff_found and silent:
                break

    if diff_found:
        detail_file.write("\n" + "*" * 10 + "\n\n")

        if isinstance(f1, str):
            detail_file.write(f"diff {f1} {f2}\nroot group:\n\n")
        else:
            detail_file.write(
                f"diff {file_1.filepath()} {file_2.filepath()}\n"
                f"group {file_1.path}:\n\n"
            )

        detail_diag = detail_subfile.getvalue()
        detail_file.write(detail_diag)

    detail_subfile.close()

    # Recurse into subgroups:

    inters_groups = groups1 & groups2

    while len(inters_groups) != 0 and (not silent or not diff_found):
        x = inters_groups.pop()
        diff_found = (
            nccmp(file_1[x], file_2[x], silent, data_only, detail_file) == 1
            or diff_found
        )

    if isinstance(f1, str):
        file_1.close()
        file_2.close()

    if diff_found:
        return 1
    else:
        return 0


if __name__ == "__main__":
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("netCDF_file", nargs=2)
    parser.add_argument("-s", "--silent", action="store_true")
    parser.add_argument(
        "-d", "--data-only", action="store_true", help="compare only data"
    )
    parser.add_argument(
        "--ign_att", nargs="+", help="list of global attributes to ignore"
    )
    args = parser.parse_args()
    nccmp_return = nccmp(
        *args.netCDF_file, args.silent, args.data_only, ign_att=args.ign_att
    )
    sys.exit(nccmp_return)
