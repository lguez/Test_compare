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

def cat_not_too_many(file, size_lim):
    """file should be an existing file object."""

    count = 0
    file.seek(0)
    while True:
        line = file.readline()
        count += 1
        if line == "" or count > size_lim: break

    if count <= size_lim:
        file.seek(0)
        for line in file: print(line, end = "")
        print()
    else:
        print("Too many lines in diff output")

def diff_txt(path_1, path_2, size_lim):
    """Treat path_1 and path_2 as text files."""

    with open(path_1) as f: fromlines = f.readlines()
    with open(path_2) as f: tolines = f.readlines()
    diff = difflib.unified_diff(fromlines, tolines, fromfile = path_1,
                                tofile = path_2)

    with tempfile.TemporaryFile("w+") as diff_out:
        diff_out.writelines(diff)
        cat_not_too_many(diff_out, size_lim)

    print()
    return 1

def diff_csv_ndiff(path_1, path_2, size_lim):
    with tempfile.TemporaryFile("w+") as ndiff_out:
        cp = subprocess.run(["ndiff", "-relerr", "1e-7", path_1, path_2],
                            stdout = ndiff_out, text = True)
        cat_not_too_many(ndiff_out, size_lim)

    print()
    return cp.returncode

def diff_csv_numdiff(path_1, path_2, size_lim):
    with tempfile.TemporaryFile("w+") as numdiff_out:
        cp = subprocess.run(["numdiff", "-r", "1e-7", path_1, path_2],
                            stdout = numdiff_out, text = True)
        cat_not_too_many(numdiff_out, size_lim)

    print()
    return cp.returncode

def my_report(dcmp, detailed_diff_instance):
    print()
    dcmp.report()
    n_diff = len(dcmp.left_only) + len(dcmp.right_only) \
        + len(dcmp.common_funny) + len(dcmp.funny_files)

    if detailed_diff_instance is None:
        n_diff += len(dcmp.diff_files)
    else:
        for name in dcmp.diff_files:
            path_1 = path.join(dcmp.left, name)
            path_2 = path.join(dcmp.right, name)
            n_diff += detailed_diff_instance.diff(path_1, path_2)

    for sub_dcmp in dcmp.subdirs.values():
        n_diff += my_report(sub_dcmp, detailed_diff_instance)

    return n_diff

class detailed_diff:
    def __init__(self, size_lim, diff_dbf = None, diff_csv = diff_csv_ndiff):
        if diff_dbf is None:
            self.diff_dbf = self.diff_dbf_dbfdump
        else:
            self.diff_dbf = diff_dbf

        self.size_lim = size_lim
        self.diff_csv = diff_csv

    def diff(self, path_1, path_2):
        print('\n*******************************************\n')
        print(path_1, path_2)
        suffix = pathlib.PurePath(path_1).suffix
        text_file = suffix == ".txt" or suffix == ".json" \
            or (suffix != ".nc" and suffix != ".csv"
                and "text" in magic.from_file(path_1))

        if text_file:
            n_diff = diff_txt(path_1, path_2, self.size_lim)
        elif suffix == ".dbf":
            n_diff = self.diff_dbf(path_1, path_2)
        elif suffix == ".csv":
            n_diff = self.diff_csv(path_1, path_2, self.size_lim)
        elif suffix == ".nc":
            n_diff = nccmp.nccmp(path_1, path_2)
        else:
            print("Detailed diff not implemented")
            n_diff = 1

        return n_diff

    def diff_dbf_dbfdump(self, path_1, path_2):
        f1_dbfdump = tempfile.NamedTemporaryFile("w+")
        f2_dbfdump = tempfile.NamedTemporaryFile("w+")
        subprocess.run(["dbfdump", path_1], stdout = f1_dbfdump)
        subprocess.run(["dbfdump", path_2], stdout = f2_dbfdump)

        if filecmp.cmp(f1_dbfdump.name, f2_dbfdump.name,
                       shallow = False):
            print(f"dbfdumps of {path_1} and {path_2} are identical")
            n_diff = 0
        else:
            n_diff = self.diff_csv(f1_dbfdump.name, f2_dbfdump.name,
                                   self.size_lim)
        f1_dbfdump.close()
        f2_dbfdump.close()
        return n_diff

parser = argparse.ArgumentParser()
parser.add_argument("directory", nargs = 2)
parser.add_argument("--pyshp", action = "store_true")
parser.add_argument("--numdiff", action = "store_true")
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

dcmp = filecmp.dircmp(*args.directory, list(ignore))

if args.brief:
    detailed_diff_instance = None
else:
    if args.pyshp:
        diff_dbf = diff_dbf.diff_dbf
    else:
        diff_dbf = None

    if args.numdiff:
        diff_csv = diff_csv_numdiff
    else:
        diff_csv = diff_csv_ndiff

    detailed_diff_instance = detailed_diff(args.limit, diff_dbf, diff_csv)

n_diff = my_report(dcmp, detailed_diff_instance)
print("\nNumber of differences:", n_diff)
if n_diff != 0: sys.exit(1)
