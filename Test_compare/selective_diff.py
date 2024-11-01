#!/usr/bin/env python3

import pathlib
import sys
import filecmp
import difflib
from os import path
import subprocess
import os
import tempfile
import fnmatch
import io
import traceback
import json
import pprint

import magic
from wand import image
import jsondiff

from . import diff_dbf
from . import diff_shp
from . import nccmp
from . import diff_gv


def cat_not_too_many(file_in, size_lim, file_out):
    """file_in and file_out should be existing file objects."""

    count = 0
    file_in.seek(0)

    while True:
        line = file_in.readline()
        count += 1
        if line == "" or count > size_lim:
            break

    if count <= size_lim:
        file_in.seek(0)
        file_out.writelines(file_in)
    else:
        file_out.write("Too many lines in diff output\n")


def diff_txt(path_1, path_2, size_lim, detail_file):
    """Process path_1 and path_2 as text files."""

    detail_file.write("\n" + "*" * 10 + "\n\n")
    detail_file.write(f"diff_txt {path_1} {path_2}\n")
    with open(path_1) as f:
        fromlines = f.readlines()
    with open(path_2) as f:
        tolines = f.readlines()
    my_diff = difflib.unified_diff(
        fromlines, tolines, fromfile=path_1, tofile=path_2, n=0
    )

    with tempfile.TemporaryFile("w+") as diff_out:
        diff_out.writelines(my_diff)
        cat_not_too_many(diff_out, size_lim, detail_file)

    detail_file.write("\n")
    return 1


def diff_png(path_1, path_2, detail_file):
    with image.Image(filename=path_1) as image1, image.Image(
        filename=path_2
    ) as image2:
        if image1.signature == image2.signature:
            # The difference must be only in metadata
            n_diff = 0
        else:
            detail_file.write("\n" + "*" * 10 + "\n\n")
            detail_file.write(f"diff_png {path_1} {path_2}\n")
            diff_img, distorsion = image2.compare(image1, metric="absolute")
            detail_file.write(f"Number of different pixels: {distorsion}\n")
            filename = path.join(path.dirname(path_2), "diff_image.png")
            diff_img.save(filename=filename)
            detail_file.write(f"See {filename}\n\n")
            n_diff = 1

    return n_diff


def diff_json(path_1, path_2, detail_file):
    with open(path_1) as f_obj_1, open(path_2) as f_obj_2:
        my_diff = jsondiff.diff(f_obj_1, f_obj_2, load=True, syntax="symmetric")

    if my_diff:
        detail_file.write("\n" + "*" * 10 + "\n\n")
        detail_file.write(f"diff_json {path_1} {path_2}\n")
        pprint.pp(my_diff, stream=detail_file)
        n_diff = 1
    else:
        n_diff = 0

    return n_diff


def max_diff_rect(path_1, path_2, detail_file, names=None):
    detail_file.write("\n" + "*" * 10 + "\n\n")

    if names is None:
        detail_file.write(f"max_diff_rect {path_1} {path_2}\n")
    else:
        detail_file.write(f"max_diff_rect {names[0]} {names[1]}\n")

    with tempfile.TemporaryFile("w+") as diff_out:
        subprocess.run(
            ["max_diff_rect", path_1, path_2],
            input="&RECTANGLE FIRST_R=2/\n&RECTANGLE /\nc\nq\n",
            text=True,
            stdout=diff_out,
        )
        diff_out.seek(0)
        detail_file.writelines(diff_out)

    detail_file.write("\n\n")
    return 1


def max_diff_nc(path_1, path_2, detail_file):
    detail_file.write("\n" + "*" * 10 + "\n\n")
    detail_file.write(f"max_diff_nc {path_1} {path_2}\n")

    with tempfile.TemporaryFile("w+") as diff_out:
        subprocess.run(
            ["max_diff_nc.sh", path_1, path_2], text=True, stdout=diff_out
        )
        diff_out.seek(0)
        detail_file.writelines(diff_out)

    return 1


def nccmp_Ziemlinski(path_1, path_2, detail_file):
    with tempfile.TemporaryFile("w+") as diff_out:
        cp = subprocess.run(
            ["nccmp", "--data", "--history", "--force", path_1, path_2],
            text=True,
            stdout=diff_out,
            stderr=subprocess.STDOUT,
        )

        if cp.returncode != 0:
            detail_file.write("\n" + "*" * 10 + "\n\n")
            detail_file.write(f"nccmp_Ziemlinski {path_1} {path_2}\n")
            detail_file.write("Comparison with nccmp by Ziemlinski:\n")
            diff_out.seek(0)
            detail_file.writelines(diff_out)

    return cp.returncode


def my_report(dcmp, detailed_diff_instance, file_out, level):
    """dcmp should be an instance of filecmp.dircmp."""

    detail_file = io.StringIO()
    n_diff = (
        len(dcmp.left_only)
        + len(dcmp.right_only)
        + len(dcmp.common_funny)
        + len(dcmp.funny_files)
    )

    if detailed_diff_instance is None:
        n_diff += len(dcmp.diff_files)
    else:
        for name in dcmp.diff_files:
            path_1 = path.join(dcmp.left, name)
            path_2 = path.join(dcmp.right, name)
            n_diff += detailed_diff_instance.diff(path_1, path_2, detail_file)

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
        n_diff += my_report(
            sub_dcmp, detailed_diff_instance, file_out, level + 1
        )

    return n_diff


class detailed_diff:
    def __init__(
        self,
        size_lim,
        diff_dbf_pyshp,
        diff_csv,
        diff_nc,
        tolerance,
        ign_att=None,
    ):
        self.size_lim = size_lim
        self.tolerance = tolerance
        self.diff_nc = diff_nc
        self.ign_att = ign_att

        if diff_dbf_pyshp:
            self._diff_dbf = diff_dbf.diff_dbf
        else:
            self._diff_dbf = self._diff_dbf_dbfdump

        if diff_csv == "numdiff":
            self._diff_csv = self._diff_csv_numdiff
        elif diff_csv == "max_diff_rect":
            self._diff_csv = max_diff_rect
        else:
            self._diff_csv = self._diff_csv_ndiff

    def diff(self, path_1, path_2, detail_file):
        suffix = pathlib.PurePath(path_1).suffix

        if suffix == ".dbf":
            n_diff = self._diff_dbf(path_1, path_2, detail_file)
        elif suffix == ".csv":
            n_diff = self._diff_csv(path_1, path_2, detail_file)
        elif suffix == ".nc":
            if self.diff_nc == "ncdump":
                n_diff = self._diff_nc_ncdump(
                    path_1, path_2, detail_file=detail_file
                )
            elif self.diff_nc == "max_diff_nc":
                n_diff = max_diff_nc(path_1, path_2, detail_file=detail_file)
            elif self.diff_nc == "Ziemlinski":
                n_diff = nccmp_Ziemlinski(
                    path_1, path_2, detail_file=detail_file
                )
            else:
                n_diff = nccmp.nccmp(
                    path_1,
                    path_2,
                    detail_file=detail_file,
                    ign_att=self.ign_att,
                )
        elif suffix == ".shp":
            n_diff = diff_shp.diff_shp(
                path_1,
                path_2,
                detail_file=detail_file,
                tolerance=self.tolerance,
            )
        elif suffix == ".png":
            n_diff = diff_png(path_1, path_2, detail_file)
        elif suffix == ".gv":
            n_diff = diff_gv.diff_gv(path_1, path_2, detail_file)
        elif suffix == ".json":
            n_diff = diff_json(path_1, path_2, detail_file)
        elif suffix == ".txt" or "text" in magic.from_file(
            path.realpath(path_1)
        ):
            n_diff = diff_txt(path_1, path_2, self.size_lim, detail_file)
        else:
            detail_file.write("\n" + "*" * 10 + "\n\n")
            detail_file.write(f"diff {path_1} {path_2}\n")
            detail_file.write("Detailed diff not implemented\n\n")
            n_diff = 1

        return n_diff

    def _diff_dbf_dbfdump(self, path_1, path_2, detail_file):
        f1_dbfdump = tempfile.NamedTemporaryFile("w+")
        f2_dbfdump = tempfile.NamedTemporaryFile("w+")
        subprocess.run(["dbfdump", path_1], stdout=f1_dbfdump)
        subprocess.run(["dbfdump", path_2], stdout=f2_dbfdump)

        if filecmp.cmp(f1_dbfdump.name, f2_dbfdump.name, shallow=False):
            n_diff = 0
        else:
            n_diff = self._diff_csv(
                f1_dbfdump.name,
                f2_dbfdump.name,
                detail_file,
                names=(path_1, path_2),
            )

        f1_dbfdump.close()
        f2_dbfdump.close()
        return n_diff

    def _diff_nc_ncdump(self, path_1, path_2, detail_file):
        f1_ncdump = tempfile.NamedTemporaryFile("w+")
        f2_ncdump = tempfile.NamedTemporaryFile("w+")
        subprocess.run(["ncdump", "-h", path_1], stdout=f1_ncdump)
        subprocess.run(["ncdump", "-h", path_2], stdout=f2_ncdump)

        if filecmp.cmp(f1_ncdump.name, f2_ncdump.name, shallow=False):
            n_diff = 0
        else:
            detail_file.write(
                f"ncdumps of headers of {path_1} and {path_2} "
                "are different\n"
            )
            n_diff = diff_txt(
                f1_ncdump.name, f2_ncdump.name, self.size_lim, detail_file
            )

        f1_ncdump.close()
        f2_ncdump.close()
        n_diff += nccmp.nccmp(
            path_1, path_2, data_only=True, detail_file=detail_file
        )
        return min(n_diff, 1)

    def _diff_csv_ndiff(self, path_1, path_2, detail_file, names=None):
        with tempfile.TemporaryFile("w+") as diff_out:
            cp = subprocess.run(
                ["ndiff", "-relerr", str(self.tolerance), path_1, path_2],
                stdout=diff_out,
                stderr=subprocess.STDOUT,
                text=True,
            )

            if cp.returncode != 0:
                detail_file.write("\n" + "*" * 10 + "\n\n")

                if names is None:
                    detail_file.write(f"ndiff {path_1} {path_2}\n")
                else:
                    detail_file.write(f"ndiff {names[0]} {names[1]}\n")

                detail_file.write(
                    "Comparison with ndiff, tolerance " f"{self.tolerance}:\n"
                )
                cat_not_too_many(diff_out, self.size_lim, detail_file)
                detail_file.write("\n")

        return cp.returncode

    def _diff_csv_numdiff(self, path_1, path_2, detail_file, names=None):
        with tempfile.TemporaryFile("w+") as diff_out:
            cp = subprocess.run(
                [
                    "numdiff",
                    "--quiet",
                    "--statistics",
                    f"--relative-tolerance={self.tolerance}",
                    path_1,
                    path_2,
                ],
                stdout=diff_out,
                stderr=subprocess.STDOUT,
                text=True,
            )

            if cp.returncode == 1:
                detail_file.write("\n" + "*" * 10 + "\n\n")

                if names is None:
                    detail_file.write(f"numdiff {path_1} {path_2}\n")
                else:
                    detail_file.write(f"numdiff {names[0]} {names[1]}\n")

                detail_file.write(
                    "Comparison with numdiff, tolerance " f"{self.tolerance}:\n"
                )
                cat_not_too_many(diff_out, self.size_lim, detail_file)
                detail_file.write("\n")
            elif cp.returncode != 0:
                diff_out.seek(0)
                sys.stdout.writelines(diff_out)
                print("selective_diff: error from numdiff")
                sys.exit(2)

        return cp.returncode


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

    # Use command-line options to define a detailed_diff instance:
    if brief:
        detailed_diff_instance = None
    else:
        if numdiff:
            diff_csv = "numdiff"
        elif max_diff_rect:
            diff_csv = "max_diff_rect"
        else:
            diff_csv = None

        if ncdump:
            diff_nc = "ncdump"
        elif max_diff_nc:
            diff_nc = "max_diff_nc"
        elif Ziemlinski:
            diff_nc = "Ziemlinski"
        else:
            diff_nc = None

        detailed_diff_instance = detailed_diff(
            limit, pyshp, diff_csv, diff_nc, tolerance, ign_att
        )

    try:
        n_diff = my_report(dcmp, detailed_diff_instance, file_out, level=1)
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


def main_cli():
    import argparse

    parser = argparse.ArgumentParser()
    add_options(parser)
    parser.add_argument("directory", nargs=2)
    args = parser.parse_args()
    selective_diff(**vars(args))
