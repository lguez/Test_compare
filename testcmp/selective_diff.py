import sys
import filecmp
from os import path
import os
import fnmatch
import io
import traceback

from testcmp import detailed_diff


def my_report(dcmp: filecmp.dircmp, d_diff, file_out, level, ign_funny=False):

    detail_file = io.StringIO()
    n_diff = len(dcmp.left_only) + len(dcmp.right_only)

    if not ign_funny:
        n_diff += +len(dcmp.common_funny) + len(dcmp.funny_files)

    if d_diff is None:
        n_diff += len(dcmp.diff_files)
    else:
        for name in dcmp.diff_files:
            path_1 = path.join(dcmp.left, name)
            path_2 = path.join(dcmp.right, name)
            n_diff += d_diff.diff(path_1, path_2, detail_file)

    if n_diff != 0:
        print(
            "\n" + level * "#",
            "diff",
            dcmp.left,
            dcmp.right,
            "\n",
            file=file_out,
        )

        if dcmp.left_only:
            dcmp.left_only.sort()
            print("Only in", dcmp.left, ":", file=file_out)

            for x in dcmp.left_only:
                print(x, file=file_out)

            file_out.write("\n")

        if dcmp.right_only:
            dcmp.right_only.sort()
            print("Only in", dcmp.right, ":", file=file_out)

            for x in dcmp.right_only:
                print(x, file=file_out)

            file_out.write("\n")

        if dcmp.same_files:
            dcmp.same_files.sort()
            print("Identical files :", file=file_out)

            for x in dcmp.same_files:
                print(x, file=file_out)

            file_out.write("\n")

        if dcmp.diff_files:
            dcmp.diff_files.sort()
            print("Differing files according to cmp:", file=file_out)

            for x in dcmp.diff_files:
                print(x, file=file_out)

            file_out.write("\n")

        if dcmp.funny_files:
            dcmp.funny_files.sort()
            print("Trouble with common files :", file=file_out)

            for x in dcmp.funny_files:
                print(x, file=file_out)

            file_out.write("\n")

        if dcmp.common_dirs:
            dcmp.common_dirs.sort()
            print("Common subdirectories :", file=file_out)

            for x in dcmp.common_dirs:
                print(x, file=file_out)

            file_out.write("\n")

        if dcmp.common_funny:
            dcmp.common_funny.sort()
            print("Common funny cases :", file=file_out)

            for x in dcmp.common_funny:
                print(x, file=file_out)

            file_out.write("\n")

        detail_diag = detail_file.getvalue()
        file_out.write(detail_diag)

    detail_file.close()

    for sub_dcmp in dcmp.subdirs.values():
        n_diff += my_report(sub_dcmp, d_diff, file_out, level + 1, ign_funny)

    return n_diff


def selective_diff(
    directory,
    exclude=None,
    brief=False,
    numdiff=False,
    max_diff_rect=False,
    ncdump=False,
    max_diff_nc=False,
    Ziemlinski=False,
    limit=50,
    pyshp=False,
    tolerance=1e-7,
    ign_att=None,
    ign_funny=False,
    file_out=sys.stdout,
):
    if not path.isdir(directory[0]) or not path.isdir(directory[1]):
        print("\nBad directories: ", *directory, file=sys.stderr)
        sys.exit(2)

    # Construct a list of files to ignore:

    ignore = set()

    if exclude:
        for my_dir in directory:
            for dirpath, dirnames, filenames in os.walk(my_dir):
                for pattern in exclude:
                    list_match = fnmatch.filter(filenames, pattern)
                    ignore.update(list_match)

    # done

    dcmp = filecmp.dircmp(*directory, list(ignore))

    # Define a detailed_diff instance:
    if brief:
        d_diff = None
    else:
        if numdiff:
            diff_csv_option = "numdiff"
        elif max_diff_rect:
            diff_csv_option = "max_diff_rect"
        else:
            diff_csv_option = None

        if ncdump:
            diff_nc = "ncdump"
        elif max_diff_nc:
            diff_nc = "max_diff_nc"
        elif Ziemlinski:
            diff_nc = "Ziemlinski"
        else:
            diff_nc = None

        d_diff = detailed_diff.DetailedDiff(
            limit, pyshp, diff_csv_option, diff_nc, tolerance, ign_att
        )

    try:
        n_diff = my_report(dcmp, d_diff, file_out, level=1, ign_funny=ign_funny)
    except Exception:
        traceback.print_exc()
        sys.exit(2)

    if n_diff == 0:
        return 0
    else:
        print("\nNumber of differences:", n_diff, file=file_out)
        return 1


def add_options(parser):
    parser.add_argument(
        "--pyshp",
        action="store_true",
        help="use pyshp to " "compare DBF files (default dbfdump)",
    )

    # CSV files:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--numdiff",
        action="store_true",
        help="use numdiff to compare CSV files (default ndiff)",
    )
    group.add_argument(
        "--max_diff_rect",
        action="store_true",
        help="use max_diff_rect to compare CSV files (default ndiff)",
    )
    parser.add_argument(
        "-t",
        "--tolerance",
        default=1e-7,
        type=float,
        help="maximum relative error for comparison of CSV files with ndiff "
        "or numdiff and comparison of SHP files (default 1e-7)",
    )

    # NetCDF files:
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--ncdump",
        action="store_true",
        help="compare headers of NetCDF files with ncdump and data with "
        "nccmp.py (default headers and data with nccmp.py)",
    )
    group.add_argument(
        "--max_diff_nc",
        action="store_true",
        help="use max_diff_nc to compare NetCDF files (default nccmp.py)",
    )
    group.add_argument(
        "--Ziemlinski",
        action="store_true",
        help="use nccmp by Ziemlinski to compare NetCDF files "
        "(default nccmp.py)",
    )
    parser.add_argument(
        "--ign_att",
        action="append",
        help="global attribute of NetCDF file to ignore",
    )

    parser.add_argument(
        "-l",
        "--limit",
        help="maximum number of lines for printing detailed differences "
        "(default 50)",
        type=int,
        default=50,
    )
    parser.add_argument(
        "-b",
        "--brief",
        help="only compare directories briefly "
        "(default: analyse each file after brief comparison of directories)",
        action="store_true",
    )
    parser.add_argument(
        "-x",
        "--exclude",
        metavar="PAT",
        action="append",
        default=[],
        help="exclude files that match shell pattern PAT",
    )
    parser.add_argument(
        "--ign_funny",
        action="store_true",
        help="do not count difference in funny files, as diagnosed by filecmp",
    )


def main_cli():
    import argparse

    parser = argparse.ArgumentParser()
    add_options(parser)

    parser.add_argument("directory", nargs=2)
    # (This is not in add_options because, for re_compare, the
    # directories to compare should not be in the command line.)

    args = parser.parse_args()
    return selective_diff(**vars(args))
