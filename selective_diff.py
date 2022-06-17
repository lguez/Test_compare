#!/usr/bin/env python3

import argparse
import pathlib
import sys
import filecmp
import difflib
from os import path
import magic
import diff_dbf
import subprocess
import os
import tempfile
import nccmp
import fnmatch
import io

def cat_not_too_many(file_in, size_lim, file_out):
    """file_in and file_out should be existing file objects."""

    count = 0
    file_in.seek(0)
    while True:
        line = file_in.readline()
        count += 1
        if line == "" or count > size_lim: break

    if count <= size_lim:
        file_in.seek(0)
        file_out.writelines(file_in)
    else:
        file_out.write("Too many lines in diff output\n")

def diff_txt(path_1, path_2, size_lim, detail_file):
    """Treat path_1 and path_2 as text files."""

    with open(path_1) as f: fromlines = f.readlines()
    with open(path_2) as f: tolines = f.readlines()
    diff = difflib.unified_diff(fromlines, tolines, fromfile = path_1,
                                tofile = path_2, n = 0)

    with tempfile.TemporaryFile("w+") as diff_out:
        diff_out.writelines(diff)
        cat_not_too_many(diff_out, size_lim, detail_file)

    detail_file.write("\n")
    return 1

def max_diff_rect(path_1, path_2, detail_file):
    with tempfile.TemporaryFile("w+") as diff_out:
        subprocess.run(["max_diff_rect", path_1, path_2],
                       input = "&RECTANGLE FIRST_R=2/\n&RECTANGLE /\nc\nq\n",
                       text = True, stdout = diff_out)
        diff_out.seek(0)
        detail_file.writelines(diff_out)

    return 1

def max_diff_nc(path_1, path_2, detail_file):
    with tempfile.TemporaryFile("w+") as diff_out:
        subprocess.run(["max_diff_nc.sh", path_1, path_2], text = True,
                       stdout = diff_out)
        diff_out.seek(0)
        detail_file.writelines(diff_out)

    return 1

def my_report(dcmp, detailed_diff_instance):
    detail_file = io.StringIO()
    n_diff = len(dcmp.left_only) + len(dcmp.right_only) \
        + len(dcmp.common_funny) + len(dcmp.funny_files)

    if detailed_diff_instance is None:
        n_diff += len(dcmp.diff_files)
    else:
        for name in dcmp.diff_files:
            path_1 = path.join(dcmp.left, name)
            path_2 = path.join(dcmp.right, name)
            n_diff += detailed_diff_instance.diff(path_1, path_2, detail_file)

    for sub_dcmp in dcmp.subdirs.values():
        n_diff += my_report(sub_dcmp, detailed_diff_instance)

    if n_diff != 0:
        dcmp.report()
        print('\n*******************************************\n')
        detail_diag = detail_file.getvalue()
        print(detail_diag)

    detail_file.close()

    return n_diff

class detailed_diff:
    def __init__(self, size_lim, diff_dbf_pyshp, diff_csv, diff_nc):
        self.size_lim = size_lim

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

        if diff_nc == "ncdump":
            self._diff_nc = self._diff_nc_ncdump
        elif diff_nc == "max_diff_nc":
            self._diff_nc = max_diff_nc
        else:
            self._diff_nc = nccmp.nccmp

    def diff(self, path_1, path_2, detail_file):
        suffix = pathlib.PurePath(path_1).suffix
        text_file = suffix == ".txt" or suffix == ".json" \
            or (suffix != ".nc" and suffix != ".csv"
                and "text" in magic.from_file(path_1))

        if text_file:
            n_diff = diff_txt(path_1, path_2, self.size_lim, detail_file)
        elif suffix == ".dbf":
            n_diff = self._diff_dbf(path_1, path_2, detail_file)
        elif suffix == ".csv":
            n_diff = self._diff_csv(path_1, path_2, detail_file)
        elif suffix == ".nc":
            n_diff = self._diff_nc(path_1, path_2, detail_file = detail_file)
        else:
            detail_file.write("Detailed diff not implemented\n")
            n_diff = 1

        if n_diff != 0:
            print(path_1, path_2)
            print('\n*******************************************\n')

        return n_diff

    def _diff_dbf_dbfdump(self, path_1, path_2, detail_file):
        f1_dbfdump = tempfile.NamedTemporaryFile("w+")
        f2_dbfdump = tempfile.NamedTemporaryFile("w+")
        subprocess.run(["dbfdump", path_1], stdout = f1_dbfdump)
        subprocess.run(["dbfdump", path_2], stdout = f2_dbfdump)

        if filecmp.cmp(f1_dbfdump.name, f2_dbfdump.name, shallow = False):
            n_diff = 0
        else:
            n_diff = self._diff_csv(f1_dbfdump.name, f2_dbfdump.name,
                                    detail_file)

        f1_dbfdump.close()
        f2_dbfdump.close()
        return n_diff

    def _diff_nc_ncdump(self, path_1, path_2, detail_file):
        f1_ncdump = tempfile.NamedTemporaryFile("w+")
        f2_ncdump = tempfile.NamedTemporaryFile("w+")
        subprocess.run(["ncdump", "-h", path_1], stdout = f1_ncdump)
        subprocess.run(["ncdump", "-h", path_2], stdout = f2_ncdump)

        if filecmp.cmp(f1_ncdump.name, f2_ncdump.name, shallow = False):
            detail_file.write(f"ncdumps of {path_1} and {path_2} are "
                              "identical\n")
            n_diff = 0
        else:
            n_diff = diff_txt(f1_ncdump.name, f2_ncdump.name, self.size_lim,
                              detail_file)

        f1_ncdump.close()
        f2_ncdump.close()
        n_diff += nccmp.nccmp(path_1, path_2, data_only = True,
                              detail_file = detail_file)
        return min(n_diff, 1)

    def _diff_csv_ndiff(self, path_1, path_2, detail_file):
        with tempfile.TemporaryFile("w+") as ndiff_out:
            cp = subprocess.run(["ndiff", "-relerr", "1e-7", path_1, path_2],
                                stdout = ndiff_out, text = True)
            cat_not_too_many(ndiff_out, self.size_lim, detail_file)

        detail_file.write("\n")
        return cp.returncode

    def _diff_csv_numdiff(self, path_1, path_2, detail_file):
        with tempfile.TemporaryFile("w+") as numdiff_out:
            cp = subprocess.run(["numdiff", "-r", "1e-7", path_1, path_2],
                                stdout = numdiff_out, text = True)
            cat_not_too_many(numdiff_out, self.size_lim, detail_file)

        detail_file.write("\n")
        return cp.returncode

parser = argparse.ArgumentParser()
parser.add_argument("directory", nargs = 2)
parser.add_argument("--pyshp", action = "store_true",
                    help = "use pyshp to compare DBF files")
group = parser.add_mutually_exclusive_group()
group.add_argument("--numdiff", action = "store_true")
group.add_argument("--max_diff_rect", action = "store_true")
group = parser.add_mutually_exclusive_group()
group.add_argument("--ncdump", action = "store_true")
group.add_argument("--max_diff_nc", action = "store_true")
parser.add_argument("-l", "--limit", help = "maximum number of lines for "
                    "printing detailed differences (default 50)", type = int,
                    default = 50)
parser.add_argument("-b", "--brief",
                    help = "only compare directories briefly (default: "
                    "analyse each file after brief comparison of directories)",
                    action = "store_true")
parser.add_argument("-x", "--exclude", metavar = 'PAT', action = "append",
                    default = [],
                    help = "exclude files that match shell pattern PAT")
args = parser.parse_args()

if not path.isdir(args.directory[0]) or not path.isdir(args.directory[1]):
    print()
    print("Bad directories: ", *args.directory)
    sys.exit(2)

# Construct a list of files to ignore:

ignore = set()

for my_dir in args.directory:
    for dirpath, dirnames, filenames in os.walk(my_dir):
        for pattern in args.exclude:
            list_match = fnmatch.filter(filenames, pattern)
            ignore.update(list_match)

# done

dcmp = filecmp.dircmp(*args.directory, list(ignore))

# Use command-line options to define a detailed_diff instance:
if args.brief:
    detailed_diff_instance = None
else:
    if args.numdiff:
        diff_csv = "numdiff"
    elif args.max_diff_rect:
        diff_csv = "max_diff_rect"
    else:
        diff_csv = None

    if args.ncdump:
        diff_nc = "ncdump"
    elif args.max_diff_nc:
        diff_nc = "max_diff_nc"
    else:
        diff_nc = None

    detailed_diff_instance = detailed_diff(args.limit, args.pyshp, diff_csv,
                                           diff_nc)

n_diff = my_report(dcmp, detailed_diff_instance)

if n_diff != 0:
    print("\nNumber of differences:", n_diff)
    sys.exit(1)
