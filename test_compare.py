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

"main_command", "description", "stdout", "symlink", "copy", "env", either
"stdin_filename" or "input", "create_file", "exclude_cmp"

"commands" is a list of commands, "command" is a single command. A
command is a list of strings or a single string. (The command includes
the executable file.)

"main_command" should be an integer value giving the 0-based index of
the main command in the list "commands". If "main_command" is absent
and "commands" is present then the last command is defined as the main
command. "env", "stdin_filename", "stdout" and "input" apply to the
main command only.

The difference between the keys "stdin_filename" and "input" is that
"input" must be the content of standard input and "stdin_filename"
must be the name of a file that will be redirected to standard
input. The value of "input" is passed through to the "input" keyword
argument of "subprocess.run". Usually, the value of "input" should end
with "\\n". If neither "stdin_filename" nor "input" is present, then
we assume that the run does not need any input: no interaction is
allowed.

"create_file" is a list of two elements: the name of the file to
create and its content.

If present, "symlink" or "copy" must be a list. Each element of
"symlink" or "copy" must itself be a string or a list of two strings
(no tuple allowed in JSON). If an element of "symlink" or "copy" is a
string then it must be the absolute path to a file that will be
sym-linked or copied to the test directory, with the same basename. It
may contain a shell pattern. If a required element is a list of two
strings then the first string must be the absolute path to a file that
will be sym-linked or copied to the test directory, with the second
string as basename. "symlink" and "copy" can both be present in a
given test description. Generally, files which will not be modified by
the test should be symlinked. An element of "symlink" or "copy" may be
a directory.

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
paths that occur repeatedly in test description file, or to make the
test description file independant of the machine. This abbreviation
file must contain a single dictionary. The strings $PWD and
$tests_old_dir will be automatically substituted in the test
description file, they should not be specified in the file containing
string substitutions.

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

def get_all_required(my_run):
    found = True

    for required_type in ["symlink", "copy"]:
        if required_type in my_run:
            assert isinstance(my_run[required_type], list)

            for required_item in my_run[required_type]:
                if isinstance(required_item, list):
                    found = get_single_required(required_item[0], my_run,
                                                required_item[1], required_type)
                else:
                    # Wildcards allowed
                    expanded_list = glob.glob(required_item)

                    if len(expanded_list) == 0:
                        print(f"\n{sys.argv[0]}: required {required_item} "
                              "does not exist.\n")
                        found = False
                    else:
                        for expanded_item in expanded_list:
                            base_dest = path.basename(expanded_item)
                            found = get_single_required(expanded_item, my_run,
                                                        base_dest,
                                                        required_type)
                            if not found: break

                if not found: break

            if not found: break

    return found

def get_single_required(src, my_run, base_dest, required_type):
    """If src exists then symlink or copy src to
    my_run["title"]/base_dest.

    """

    found = path.exists(src)
    
    if found:
        dst = path.join(my_run["title"], base_dest)

        if required_type == "symlink":
            os.symlink(src, dst)
        else:
            # required_type == "copy"
            if path.isfile(src):
                shutil.copyfile(src, dst)
            else:
                shutil.copytree(src, dst)
    else:
        print("\nIn", my_run["test_series_file"])
        print(sys.argv[0] + ": required " + src + " does not exist.\n")

    return found

def run_single_test(my_run, path_failed):
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

        with open("timing_test_compare.txt", "w") as f:
            t1 = time.perf_counter()
            line = "Elapsed time: {:.0f} s\n".format(t1 - t0_single_run)
            f.write(line)

        os.chdir("..")
        test_return_code = 0
    else:
        os.chdir("..")
        path_failed.touch()
        print("failed")
        test_return_code = 1

    return test_return_code

def run_tests(my_runs, allowed_keys, compare_dir, other_args):
    """my_runs should be a list of dictionaries, allowed_keys a set."""

    print("Starting runs at", datetime.datetime.now())
    t0 = time.perf_counter()
    n_failed = 0
    cumul_return = 0
    
    for i, my_run in enumerate(my_runs):
        print(i, end = ": ")
        path_failed = pathlib.Path(my_run["title"], "failed")
        previous_failed = path_failed.exists()
        
        if path.exists(my_run["title"]) and not previous_failed:
            print("Skipping", my_run["title"], "(already exists, did not fail)")
        else:
            if not set(my_run) <= allowed_keys:
                print("bad keys:")
                print(set(my_run) - allowed_keys)
                sys.exit(1)

            if previous_failed:
                print("Replacing", my_run["title"],
                      "because previous run failed...")
                shutil.rmtree(my_run["title"])
            else:
                print("Creating", my_run["title"] + "...", flush = True)

            os.mkdir(my_run["title"])
            found = get_all_required(my_run)

            if found:
                n_failed += run_single_test(my_run, path_failed)
            else:
                shutil.rmtree(my_run["title"])

        if not path_failed.exists():
            old_dir = path.join(compare_dir, my_run["title"])

            try:
                shutil.copytree(my_run["title"], old_dir, symlinks = True)
            except FileNotFoundError:
                pass
            except FileExistsError:
                cumul_return += compare(my_run, compare_dir, other_args)
            else:
                print("Archived", my_run["title"])

    print("Elapsed time:", time.perf_counter() - t0, "s")
    print("Number of failed runs:", n_failed)
    print("cumul_return =", cumul_return)

def compare(my_run, compare_dir, other_args):
    path_comp_code = path.join(my_run["title"], "comparison_code.txt")

    if path.exists(path_comp_code):
        with open(path_comp_code) as f: comparison_code = f.readline()[:- 1]
        comparison_code = int(comparison_code)
    else:
        t0 = time.perf_counter()
        old_dir = path.join(compare_dir, my_run["title"])
        subprocess_args = ["selective_diff.py",
                           "--exclude=timing_test_compare.txt",
                           old_dir, my_run["title"]]
        subprocess_args[1:1] = other_args

        if "exclude_cmp" in my_run:
            assert isinstance(my_run["exclude_cmp"], list)

            for pat in my_run["exclude_cmp"]:
                subprocess_args[1:1] = ["-x",  pat]

        with open("comparison.txt", "w") as f:
            cp = subprocess.run(subprocess_args, stdout = f,
                                stderr = subprocess.STDOUT)
            f.write("\n" + ("*" * 10 + "\n") * 2 + "\n")

        if cp.returncode in [0, 1]:
            comparison_code = cp.returncode
            with open(path_comp_code, "w") as f: f.write(f"{cp.returncode}\n")

            if cp.returncode == 0:
                os.remove("comparison.txt")
            else:
                dst = path.join(my_run["title"], "comparison.txt")
                os.rename("comparison.txt", dst)
        else:
            print("Problem in selective_diff.py, return code "
                  "should be 0 or 1.\nSee \"comparison.txt\".")
            cp.check_returncode()

        t1 = time.perf_counter()
        line = "Elapsed time for comparison: {:.0f} s\n".format(t1 - t0)
        fname = path.join(my_run["title"], "timing_test_compare.txt")
        with open(fname, "a") as f: f.write(line)

    return comparison_code

parser = argparse.ArgumentParser(description = __doc__, formatter_class \
                                 = argparse.RawDescriptionHelpFormatter,
                                 epilog = 'Remaining options are passed on to '
                                 '"selective_diff.py". Use long form for '
                                 'options of "selective_diff.py" with '
                                 'arguments.')
parser.add_argument("compare_dir", help = "Directory containing old runs "
                    "for comparison, after running the tests")
parser.add_argument("test_descr", nargs = "+",
                    help = "JSON file containing description of tests")
parser.add_argument("-s", "--substitutions", help="JSON input file containing "
                    "abbreviations for directory names")
parser.add_argument("--clean", help = """
Remove any existing run directories in the current directory. With -t, remove 
only the selected run directory, if it exists.""",
                    action = "store_true")
parser.add_argument("-l", "--list", help = "just list the titles",
                    action = "store_true")
parser.add_argument("-t", "--title", help = "select a title in JSON file")
args, other_args = parser.parse_known_args()

my_runs = []

if args.list:
    for test_descr in args.test_descr:
        with open(test_descr) as input_file: series = json.load(input_file)
        my_runs.extend(series)

    for my_run in my_runs: print(my_run["title"])
else:
    if not path.isdir(args.compare_dir):
        sys.exit("Directory " + args.compare_dir + " not found.")

    if args.substitutions:
        with open(args.substitutions) as subst_file:
            substitutions = json.load(subst_file)
    else:
        substitutions = {}

    substitutions["PWD"] = os.getcwd()
    substitutions["tests_old_dir"] = path.abspath(args.compare_dir)

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
    else:
        allowed_keys = {"title", "command", "commands", "main_command",
                        "description", "stdout", "symlink", "copy", "env",
                        "stdin_filename", "input", "test_series_file",
                        "create_file", "exclude_cmp"}

        while True:
            run_tests(my_runs, allowed_keys, args.compare_dir, other_args)
            reply = input("Replace old runs? ")
            reply = reply.casefold()

            if not reply.startswith("y"): break

            for my_run in my_runs:
                if path.exists(my_run["title"]) and not \
                   pathlib.Path(my_run["title"], "failed").exists():
                    path_comp_code =path.join(my_run["title"],
                                              "comparison_code.txt")

                    with open(path_comp_code) as f:
                        comparison_code = f.readline()[:- 1]

                    if int(comparison_code) == 1:
                        print("Replacing", my_run["title"])
                        old_dir = path.join(args.compare_dir, my_run["title"])
                        if path.exists(old_dir): shutil.rmtree(old_dir)
                        os.remove(path_comp_code)
                        fname = path.join(my_run["title"], "comparison.txt")
                        os.remove(fname)
                        shutil.move(my_run["title"], old_dir)

        reply = input("Remove new runs? ")
        reply = reply.casefold()

        if reply.startswith("y"):
            for my_run in my_runs: shutil.rmtree(my_run["title"])
