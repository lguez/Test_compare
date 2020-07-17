#!/usr/bin/env python3

"""Requires Python >= 3.5.

This script chains runs in directories which do not pre-exist and are
created.

This script reads a JSON test description file. The test description
file must contain a list of dictionaries. Each run is defined by
title, commands, required files (that is, files required to be present
in the current directory at run time), stdin_filename or input, and
stdout file. The title is used as directory name. Each dictionary must
thus include the keys:

"title", either "command" or "commands"

and may also include the keys:

"description", "stdout", "required", either "stdin_filename" or "input"

"commands" is a list of commands, "command" is a single command. A
command is a list of strings or a single string. (The command includes
the executable file.)

If "commands" is present then "stdin_filename", "stdout" and "input"
apply to the last command only.

The difference between the keys "stdin_filename" and "input" is that
"input" must be the content of standard input and stdin_filename must
be the name of a file that will be redirected to standard input. The
value of "input" is passed through to the "input" keyword argument of
"subprocess.run". If neither "stdin_filename" nor "input" is present,
then we assume that the run does not need any input: no interaction is
allowed.

If present, "required" must be a list. Each element of "required" must
itself be a string or a list of two strings (no tuple allowed in
JSON). If a required element is a string then it must be the absolute
path to a file that will be sym-linked to the test directory, with the
same basename. If a required element is a list of two strings then the
first string must be the absolute path to a file that will be
sym-linked to the test directory, with the second string as basename.

If "stdout" is not present then the file name for standard output is
constructed from the name of the executable file.

The required files and executables must be specified in the JSON input
file with absolute paths. File arguments in commands, if any, also
have to be specified with absolute paths.

This script can also read a JSON file containing string substitutions
to be made in the test description file. This is useful to abbreviate
paths that occur repeatedly in test description file. This
abbreviation file must contain a single dictionary.

"""

import argparse
import csv
import datetime
import glob
import json
import os
from os import path
import shutil
import subprocess
import sys
import tempfile
import time
import string

def my_symlink(src, run_dir, base_dest):
    """If src does not exist, remove run_dir, else symlink src to
    run_dir/base_dest.

    """
    
    if not path.exists(src):
        shutil.rmtree(run_dir)
        print()
        sys.exit(sys.argv[0] + ": required " + src + " does not exist.")

    dst = path.join(run_dir, base_dest)
    os.symlink(src, dst)
    
def run_tests(my_runs):
    """my_runs should be a list of dictionaries."""

    perf_report = open("perf_report.csv", "w", newline='')
    writer = csv.writer(perf_report)
    writer.writerow(["Name of test", "elapsed time, in s"])
    print("Starting runs at", datetime.datetime.now())
    t0 = time.perf_counter()
    
    for i, my_run in enumerate(my_runs):
        print(i, end = ": ")
        
        if path.exists(my_run["title"]):
            print("Skipping", my_run["title"], "(already exists)") 
        else:
            print("Creating", my_run["title"] + "...", flush = True)
            os.mkdir(my_run["title"])

            if "required" in my_run:
                assert isinstance(my_run["required"], list)
                
                for required_item in my_run["required"]:
                    if isinstance(required_item, list):
                        my_symlink(required_item[0], my_run["title"],
                                   required_item[1])
                    else:
                        # Wildcards allowed
                        expanded_list = glob.glob(required_item)
                        
                        if len(expanded_list) == 0:
                            shutil.rmtree(my_run["title"])
                            print()
                            sys.exit(sys.argv[0] + ": required "
                                     + required_item + " does not exist.")
                        else:
                            for expanded_item in expanded_list:
                                base_dest = path.basename(expanded_item)
                                my_symlink(expanded_item, my_run["title"],
                                           base_dest)

            if "command" in my_run:
                commands = [my_run["command"]]
            else:
                commands = my_run["commands"]
                
            if "stdout" in my_run:
                stdout_filename = my_run["stdout"]
            else:
                if isinstance(commands[-1], list):
                     stdout_filename = commands[-1][0]
                else:
                     stdout_filename = commands[-1]

                stdout_filename = path.basename(stdout_filename)
                stdout_filename = path.splitext(stdout_filename)[0] \
                                  + "_stdout.txt"

            if "stdin_filename" in my_run and "input" in my_run:
                print(my_run["title"],
                      ": stdin_filename and input are exclusive.")
                shutil.rmtree(my_run["title"])
                sys.exit(1)

            input_kwds = {}

            if "stdin_filename" in my_run:
                input_kwds["stdin"] = open(my_run["stdin_filename"])
            elif "input" in my_run:
                input_kwds["input"] = my_run["input"]
            else:
                input_kwds["stdin"] = subprocess.DEVNULL

            os.chdir(my_run["title"])

            with open("test.json", "w") as f:
                json.dump(my_run, f, indent = 3, sort_keys = True)
                f.write("\n")

            t0_single_run = time.perf_counter()

            for command in commands[:-1]:
                subprocess.run(command, check = True)
                
            with open(stdout_filename, "w") as stdout:
                try:
                    subprocess.run(commands[-1], stdout = stdout,
                                   stderr = subprocess.STDOUT, check = True,
                                   universal_newlines = True, **input_kwds)
                except subprocess.CalledProcessError:
                    print()
                    if "stdin_filename" in my_run:
                        print("stdin_filename:", my_run["stdin_filename"])
                    raise

            writer.writerow([my_run["title"], format(time.perf_counter()
                                                     - t0_single_run, ".0f")])
            os.chdir("..")

    print("Elapsed time:", time.perf_counter() - t0, "s")
    perf_report.close()

parser = argparse.ArgumentParser(description = __doc__,
                                 formatter_class = argparse.RawDescriptionHelpFormatter)
parser.add_argument("test_descr",
                    help = "JSON file containing description of tests")
parser.add_argument("-d", "--dirnames", help="JSON input file containing "
                    "abbreviations for directory names")
parser.add_argument("-c", "--compare", help = "Directory containing old runs "
                    "for comparison, after running the tests")
parser.add_argument("-x", "--exclude", help = "exclude files that match shell "
                    "pattern PAT from comparison, after running the tests",
                    metavar = "PAT", action = "append")
parser.add_argument("--clean", help = """
Remove any existing run directories in the current directory before
new runs. With -t, remove only the selected run directory, if it
exists, before running.""",
                    action = "store_true")
parser.add_argument("-t", "--title", help = "select a title in JSON file")
args = parser.parse_args()

if args.compare:
    if not path.isdir(args.compare):
        sys.exit("Directory " + args.compare + " not found.")

if args.dirnames:
    with open(args.dirnames) as subst_file:
        substitutions = json.load(subst_file)
else:
    substitutions = {}

substitutions["PWD"] = os.getcwd()

with tempfile.TemporaryFile(mode = "w+") as json_substituted, \
     open(args.test_descr) as input_file:
    for line in input_file:
        line = string.Template(line).substitute(substitutions)
        json_substituted.write(line)

    json_substituted.seek(0)
    my_runs = json.load(json_substituted)

if args.title:
    for my_run in my_runs:
        if my_run["title"] == args.title: break
    else:
        sys.exit(args.title + " is not a title in the JSON input file.")

    my_runs = [my_run]
    
print("Number of runs:", len(my_runs))

if args.clean:
    for my_run in my_runs:
        if path.exists(my_run["title"]):
            print("Removing", my_run["title"] + "...")
            shutil.rmtree(my_run["title"])

if args.compare:
    while True:
        run_tests(my_runs)
        cumul_return = 0
        print("Comparing...")

        with open("comparison.txt", "w") as comparison_file:
            for my_run in my_runs:
                old_dir = path.join(args.compare, my_run["title"])
                subprocess_args = ["selective_diff.sh", old_dir,
                                   my_run["title"]]
                
                if args.exclude:
                    for pat in args.exclude:
                        subprocess_args[1:1] = ["-x",  pat]
                        
                cp = subprocess.run(subprocess_args, stdout = comparison_file,
                                    stderr = subprocess.STDOUT)
                
                if cp.returncode in [0, 1]:
                    cumul_return += cp.returncode

                    if cp.returncode == 1:
                        comparison_file.write('****************\n' * 2)
                        comparison_file.flush()
                else:
                    print("Problem in selective_diff.sh, return code "
                          "should be 0 or 1.\nSee \"comparison.txt\".")
                    cp.check_returncode()

        print("Created file \"comparison.txt\".")
        print("cumul_return =", cumul_return)
        reply = input("Remove old runs? ")
        reply = reply.casefold()

        if not reply.startswith("y"): break

        for my_run in my_runs:
            old_dir = path.join(args.compare, my_run["title"])
            shutil.rmtree(old_dir)
            shutil.move(my_run["title"], old_dir)

        dst = path.join(args.compare, "perf_report.csv")
        os.rename("perf_report.csv", dst)

    reply = input("Remove new runs? ")
    reply = reply.casefold()

    if reply.startswith("y"): 
        for my_run in my_runs: shutil.rmtree(my_run["title"])

    reply = input("Replace old performance report? ")
    reply = reply.casefold()

    if reply.startswith("y"):
        dst = path.join(args.compare, "perf_report.csv")
        os.rename("perf_report.csv", dst)
else:
    run_tests(my_runs)
