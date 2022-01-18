#!/usr/bin/env python3

"""Author: Lionel GUEZ

Selective analysis of differences between directories based on file
type and amount of difference. This script first compares briefly
two directories. The two directories should be given as arguments of
the script. If the directories contains text or DBF files with the
same name and modestly different content then the script prints the
detailed difference between them. If the directories contain NetCDF
files with the same name and different content then the script
compares further the header and data parts. The script prints the
detailed differences between the header part, and between the dumps
of the data parts if the number of different lines is small
enough. The script optionally:

- creates a NetCDF file with the NCO operator "ncbo" containing the
difference and the relative difference between the original NetCDF
files;

- computes statistics of the differences.

The user of this script needs to have the permission to write in the
current directory.

Non-standard utilities invoked in this script: ncdump, NCO,
nccmp.py, max_diff_nc.sh, dbfdump, ndiff by Nelson Beebe,
numdiff. ndiff and numdiff are not completely redundant.

An exit status of 0 means no differences were found, 1 means some
differences were found, and 2 means trouble.

"""

import netCDF4
from os import path
import argparse
import pathlib
import sys
import os
import re
import subprocess
import filecmp
import magic
import diff_dbf
import fnmatch

def cat_not_too_many(file, size_lim):
    count = 0
    
    with open(file) as f:
        while True:
            line = f.readline()
            count += 1
            if line == "" or count > size_lim: break

        if count < size_lim:
            f.seek(0)
            for line in f: print(line, end = "")
            print()
        else:
            print("Too many lines in diff output")


parser = argparse.ArgumentParser()
parser.add_argument("directory", nargs = 2)
parser.add_argument("-d", "--subtract",
                    help = "create a NetCDF file containing differences "
                    "for NetCDF files with different data parts",
                    action = "store_true")
parser.add_argument("-l", "--limit", help = "maximum number of lines for "
                    "printing detailed differences (default 50)", type = int,
                    default = 50)
parser.add_argument("-s", "--statistics",
                    help = "compute statistics for NetCDF files with "
                    "different data parts", action = "store_true")
parser.add_argument("-b", "--brief",
                    help = "only compare directories briefly (default: "
                    "analyse each file after brief comparison of directories)",
                    action = "store_true")
parser.add_argument("-r", "--report_identical",
                    help = "report indentical directories",
                    action = "store_true")
parser.add_argument("-x", metavar = 'PAT', action = "append", default = [],
                    help = "exclude files that match shell pattern PAT")
args = parser.parse_args()
dir1 = pathlib.Path(args.directory[0])
dir2 = pathlib.Path(args.directory[1])

if not dir1.is_dir() or not dir2.is_dir():
    print()
    print("Directories: ", args.directory)
    sys.exit("Bad directories")

# Compare directories briefly:

exclude_options = []

for p in args.x: exclude_options.extend(["-x", p])

p_diff = subprocess.Popen(["diff", "--recursive", "--brief"] + exclude_options
                           + [dir1, dir2], text = True,
                          stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
completed_process = subprocess.run(["grep", "^Only in "], text = True,
                                   stdin = p_diff.stdout, capture_output = True)

n_diff=0
# (number of differing files)

n_id=0
# (number of identical files)

initial_dir = os.getcwd()
os.chdir(dir1)
file_list = []

for dirpath, dirnames, filenames in os.walk(os.curdir):
    for filename in filenames:
        my_path = path.join(dirpath, filename)

        if not path.islink(my_path):
            for p in args.x:
                if fnmatch.fnmatch(filename, p): break
            else:
                file_list.append(my_path)

os.chdir(initial_dir)
diff_file = []
id_file = []

for filename in file_list:
    path_2 = path.join(dir2, filename)

    if os.access(path_2, os.F_OK):
        # We have a file with the same name in the two directories
        path_1 = path.join(dir1, filename)
        equal = filecmp.cmp(path_1, path_2, shallow = False)
        
        if not equal:
            # Different content
            n_diff += 1
            diff_file.append(filename)
        else:
            # Same content
            n_id += 1
            id_file.append(filename)

if args.report_identical or len(completed_process.stdout) != 0 or n_diff != 0:
    print("\nDirectories:", *args.directory)
    print(completed_process.stdout)
    print("Differing files:")
    print()
    print(*diff_file, sep = '\n')
    print()
    print("Number of files found:")
    print(len(diff_file))
    print()
    print("Identical files:")
    print()
    print(*id_file, sep = "\n")
    print()
    print("Number of files found:")
    print(len(id_file))
    print()

    if not args.brief:
        # Analyse each file
        for name in diff_file:
            path_1 = path.join(dir1, name)
            path_2 = path.join(dir2, name)
            if not os.access(path_1, os.F_OK):
                print("Broken link:", path_1)
            elif not os.access(path_2, os.F_OK):
                print("Broken link:", path_2)
            else:
                suffix = pathlib.PurePath(name).suffix
                text_file = suffix == ".txt" or suffix == ".json" \
                    or (suffix != ".nc" and suffix != ".csv"
                        and "text" in magic.from_file(path_1))

                if text_file or re.fullmatch(".nc|.dbf|.csv", suffix):
                    # We have a text, NetCDF, DBF or CSV file
                    name0 = pathlib.Path(name).stem
                    print()
                    print('*******************************************')
                    print()
                    print(name)

                    if text_file:
                        with open("diff_out", "w") as f:
                            subprocess.run(["diff", "--ignore-all-space",
                                            path_1, path_2], stdout = f,
                                           text = True)
                        
                        if path.getsize("diff_out") == 0:
                            print("Only white space difference")
                        else:
                            cat_not_too_many("diff_out", args.limit)
                        
                        print()
                        os.remove("diff_out")
                    elif suffix == ".dbf":
                        diff_dbf.diff_dbf(path_1, path_2)
                    elif suffix == ".csv":
                        with open("ndiff_out", "w") as f:
                            subprocess.run(["ndiff", "-relerr", "1e-7", path_1,
                                            path_2], stdout = f, text = True)
                        
                        cat_not_too_many("ndiff_out", args.limit)
                        print()
                    else:
                        nccmp(path_1, path_2)

if n_diff != 0 or len(completed_process.stdout) != 0: sys.exit(1)
