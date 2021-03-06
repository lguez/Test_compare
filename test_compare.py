#!/usr/bin/env python3

"""Requires Python >= 3.5.

This script chains runs in directories which do not pre-exist and are
created.

This script reads a JSON test description file. The test description
file must contain a list of dictionaries. Each run is defined by
title, commands, required files (that is, files required to be present
in the current directory at run time), environment, stdin_filename or
input, and stdout file. The title is used as directory name. Each
dictionary must thus include the keys:

"title", either "command" or "commands"

and may also include the keys:

"main_command", "description", "stdout", "required", "env", either
"stdin_filename" or "input"

"commands" is a list of commands, "command" is a single command. A
command is a list of strings or a single string. (The command includes
the executable file.)

"main_command" should be an integer value giving the 0-based index of
the main command in the list "commands". If "main_command" is absent
and "commands" is present then the last command is defined as the main
command. "stdin_filename", "stdout" and "input" apply to the main
command only.

The difference between the keys "stdin_filename" and "input" is that
"input" must be the content of standard input and "stdin_filename"
must be the name of a file that will be redirected to standard
input. The value of "input" is passed through to the "input" keyword
argument of "subprocess.run". If neither "stdin_filename" nor "input"
is present, then we assume that the run does not need any input: no
interaction is allowed.

If present, "required" must be a list. Each element of "required" must
itself be a string or a list of two strings (no tuple allowed in
JSON). If a required element is a string then it must be the absolute
path to a file that will be sym-linked to the test directory, with the
same basename. It may contain a shell pattern. If a required element
is a list of two strings then the first string must be the absolute
path to a file that will be sym-linked to the test directory, with the
second string as basename.

If present, "env" must be a dictionary of environment variables and
values. This dictionary will be added to, not replace, the inherited
environment. If an environment variable in "env" was already in the
environment, the value in "env" replaces the old value. This
environment is applied only to the main command.

If "stdout" is not present then the file name for standard output is
constructed from the name of the main command (determined by
"main_command").

The required files and executables must be specified in the JSON input
file with absolute paths. File arguments in commands, if any, also
have to be specified with absolute paths.

This script can also read a JSON file containing string substitutions
to be made in the test description file. This is useful to abbreviate
paths that occur repeatedly in test description file. This
abbreviation file must contain a single dictionary.

There may be several JSON test description files on the command
line. If two tests have the same name, the second one will be skipped.

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
import pathlib

def my_symlink(src, my_run, base_dest):
    """If src does not exist, remove my_run["title"], else symlink src to
    my_run["title"]/base_dest.

    """
    
    if not path.exists(src):
        shutil.rmtree(my_run["title"])
        print()
        print("In", my_run["test_series_file"])
        sys.exit(sys.argv[0] + ": required " + src + " does not exist.")

    dst = path.join(my_run["title"], base_dest)
    os.symlink(src, dst)
    
def run_single_test(previous_failed, my_run, writer, p_failed):
    if previous_failed:
        print("Replacing", my_run["title"], "because previous run failed...")
        shutil.rmtree(my_run["title"])
    else:
        print("Creating", my_run["title"] + "...", flush = True)

    os.mkdir(my_run["title"])

    if "required" in my_run:
        assert isinstance(my_run["required"], list)

        for required_item in my_run["required"]:
            if isinstance(required_item, list):
                my_symlink(required_item[0], my_run, required_item[1])
            else:
                # Wildcards allowed
                expanded_list = glob.glob(required_item)

                if len(expanded_list) == 0:
                    shutil.rmtree(my_run["title"])
                    print()
                    sys.exit(f"{sys.argv[0]}: required {required_item} "
                             "does not exist.")
                else:
                    for expanded_item in expanded_list:
                        base_dest = path.basename(expanded_item)
                        my_symlink(expanded_item, my_run, base_dest)

    if "command" in my_run:
        commands = [my_run["command"]]
        main_command = 0
    else:
        commands = my_run["commands"]

        if "main_command" in my_run:
            main_command = my_run["main_command"]
        else:
            main_command = len(commands) - 1

    if "stdout" in my_run:
        stdout_filename = my_run["stdout"]
    else:
        if isinstance(commands[main_command], list):
             stdout_filename = commands[main_command][0]
        else:
             stdout_filename = commands[main_command]

        stdout_filename = path.basename(stdout_filename)
        stdout_filename = path.splitext(stdout_filename)[0] + "_stdout.txt"

    stderr_filename = stdout_filename.replace("_stdout.txt", "_stderr.txt")

    if "stdin_filename" in my_run and "input" in my_run:
        print(my_run["title"], ": stdin_filename and input are exclusive.")
        shutil.rmtree(my_run["title"])
        sys.exit(1)

    other_kwargs = {}

    if "stdin_filename" in my_run:
        try:
            other_kwargs["stdin"] = open(my_run["stdin_filename"])
        except FileNotFoundError:
            shutil.rmtree(my_run["title"])
            raise
    elif "input" in my_run:
        other_kwargs["input"] = my_run["input"]
    else:
        other_kwargs["stdin"] = subprocess.DEVNULL

    if "env" in my_run:
        other_kwargs["env"] = dict(os.environ, **my_run["env"])

    os.chdir(my_run["title"])

    if "create_file" in my_run:
        with open(my_run["create_file"][0], "w") as f:
            f.write(my_run["create_file"][1])
        
    with open("test.json", "w") as f:
        json.dump(my_run, f, indent = 3, sort_keys = True)
        f.write("\n")

    t0_single_run = time.perf_counter()

    for command in commands[:main_command]:
        subprocess.run(command, check = True)

    with open(stdout_filename, "w") as stdout, open(stderr_filename, "w") \
         as stderr:
        cp = subprocess.run(commands[main_command], stdout = stdout,
                            stderr = stderr, universal_newlines = True,
                            **other_kwargs)

    if cp.returncode == 0:
        for command in commands[main_command + 1:]:
            subprocess.run(command, check = True)

        writer.writerow([my_run["title"],
                         format(time.perf_counter() - t0_single_run, ".0f")])
        os.chdir("..")
    else:
        os.chdir("..")
        p_failed.touch()
        print("failed")

def run_tests(my_runs):
    """my_runs should be a list of dictionaries."""

    perf_report = open("perf_report.csv", "w", newline='')
    writer = csv.writer(perf_report, lineterminator = "\n")
    writer.writerow(["Name of test", "elapsed time, in s"])
    print("Starting runs at", datetime.datetime.now())
    t0 = time.perf_counter()
    
    for i, my_run in enumerate(my_runs):
        print(i, end = ": ")
        p_failed = pathlib.Path(my_run["title"], "failed")
        previous_failed = p_failed.exists()
        
        if path.exists(my_run["title"]) and not previous_failed:
            print("Skipping", my_run["title"], "(already exists)") 
        else:
            run_single_test(previous_failed, my_run, writer, p_failed)

    print("Elapsed time:", time.perf_counter() - t0, "s")
    perf_report.close()

parser = argparse.ArgumentParser(description = __doc__, formatter_class \
                                 = argparse.RawDescriptionHelpFormatter)
parser.add_argument("test_descr", nargs = "+",
                    help = "JSON file containing description of tests")
parser.add_argument("-s", "--substitutions", help="JSON input file containing "
                    "abbreviations for directory names")
group = parser.add_mutually_exclusive_group()
group.add_argument("-c", "--compare", help = "Directory containing old runs "
                    "for comparison, after running the tests")
group.add_argument("-a", "--archive", help = "Directory to which dirs will be "
                    "copied, after running the tests")
parser.add_argument("-b", "--brief", help = "compare briefly",
                    action = "store_true")
parser.add_argument("-x", "--exclude", help = "exclude files that match shell "
                    "pattern PAT from comparison, after running the tests",
                    metavar = "PAT", action = "append")
parser.add_argument("--clean", help = """
Remove any existing run directories in the current directory before
new runs. With -t, remove only the selected run directory, if it
exists, before running.""",
                    action = "store_true")
parser.add_argument("-l", "--list", help = "just list the titles",
                    action = "store_true")
parser.add_argument("-t", "--title", help = "select a title in JSON file")
args = parser.parse_args()

my_runs = []

if args.list:
    for test_descr in args.test_descr:
        with open(test_descr) as input_file: series = json.load(input_file)
        my_runs.extend(series)

    for my_run in my_runs: print(my_run["title"])
else:
    if args.compare or args.archive:
        my_dir = args.compare or args.archive
        
        if not path.isdir(my_dir):
            sys.exit("Directory " + my_dir + " not found.")

    if args.substitutions:
        with open(args.substitutions) as subst_file:
            substitutions = json.load(subst_file)
    else:
        substitutions = {}

    substitutions["PWD"] = os.getcwd()

    for test_descr in args.test_descr:
        try:
            input_file = open(test_descr)
        except FileNotFoundError:
            print("Skipping", test_descr, ", not found")
        else:
            with tempfile.TemporaryFile(mode = "w+") as json_substituted:
                for line in input_file:
                    line = string.Template(line).substitute(substitutions)
                    json_substituted.write(line)

                json_substituted.seek(0)
                series = json.load(json_substituted)

            input_file.close()
            for my_run in series: my_run["test_series_file"] = test_descr
            my_runs.extend(series)

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
            t0 = time.perf_counter()

            with open("comparison.txt", "w") as comparison_file:
                for my_run in my_runs:
                    old_dir = path.join(args.compare, my_run["title"])
                    subprocess_args = ["selective_diff.py", old_dir,
                                       my_run["title"]]

                    if args.exclude:
                        for pat in args.exclude:
                            subprocess_args[1:1] = ["-x",  pat]

                    if "exclude_cmp" in my_run:
                        for pat in my_run["exclude_cmp"]:
                            subprocess_args[1:1] = ["-x",  pat]

                    if args.brief: subprocess_args.insert(1, "-b")
                    cp = subprocess.run(subprocess_args,
                                        stdout = comparison_file,
                                        stderr = subprocess.STDOUT)

                    if cp.returncode in [0, 1]:
                        cumul_return += cp.returncode

                        if cp.returncode == 1:
                            comparison_file.write('****************\n' * 2)
                            comparison_file.flush()
                    else:
                        print("Problem in selective_diff.py, return code "
                              "should be 0 or 1.\nSee \"comparison.txt\".")
                        cp.check_returncode()

            print("Elapsed time for comparisons:", time.perf_counter() - t0,
                  "s")
            print("Created file \"comparison.txt\".")
            print("cumul_return =", cumul_return)
            reply = input("Remove old runs? ")
            reply = reply.casefold()

            if not reply.startswith("y"): break

            for my_run in my_runs:
                old_dir = path.join(args.compare, my_run["title"])
                if path.exists(old_dir): shutil.rmtree(old_dir)
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
        
        if args.archive:
            for my_run in my_runs:
                archive_dir = path.join(args.archive, my_run["title"])
                
                try:
                    shutil.copytree(my_run["title"], archive_dir,
                                    symlinks = True)
                except FileExistsError:
                    pass
                else:
                    print("Archived", my_run["title"])
