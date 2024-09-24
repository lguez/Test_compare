#!/usr/bin/env python3

"""This script chains runs in directories which do not pre-exist and are
created.

This script reads a JSON test description file. The test description
file must contain a dictionary. The keys of this dictionary should be
the titles of the test. Each title is a string and is used as
directory name. The value for each title is a dictionary describing a
run. Each run is defined by commands, required files (that is, files
required to be present in the current directory at run time),
environment, stdin_filename or input, and stdout file. Each dictionary
must thus include either the key "command" or "commands", and may also
include the keys:

"main_command", "description", "stdout", "symlink", "copy", "env", either
"stdin_filename" or "input", "create_file", "sel_diff_args"

"commands" is a list of commands, "command" is a single command. A
command is a list of strings or a single string. If the command is a
single string then it is split at whitespace. (The command includes
the executable file.)

"main_command" should be an integer value giving the 0-based index of
the main command in the list "commands". If "main_command" is absent
and "commands" is present then the last command is defined as the main
command. "env", "stdin_filename", "input" apply to the main command
only. The standard output of all the commands is redirected to the
file pointed by "stdout".

The difference between the keys "stdin_filename" and "input" is that
"input" must be the content of standard input and "stdin_filename"
must be the name of a file that will be redirected to standard
input. "stdin_filename" may be a relative path: it is evaluated after
changing directory to the directory of the test. "stdin_filename" may
be the file created by "create_file": it is opened after creating the
file. The value of "input" is passed through to the "input" keyword
argument of "subprocess.run". Usually, the value of "input" should end
with "\\n". If neither "stdin_filename" nor "input" is present, then
we assume that the run does not need any input: no interaction is
allowed.

"create_file" is a list of two elements: the name of the file to
create and its content. The name of the file will normally be a
relative path and the file will be created in the directory of the
test.

If present, "symlink" or "copy" must be a list. Each element of
"symlink" or "copy" must itself be a string or a list of two strings
(no tuple allowed in JSON). If an element of "symlink" or "copy" is a
string then it must be the absolute path to a file or directory that
will be sym-linked or copied to the test directory, with the same
basename. It may contain a shell pattern. If a required element is a
list of two strings then the first string must be the absolute path to
a file or directory that will be sym-linked or copied to the test
directory, with the second string as basename. "symlink" and "copy"
can both be present in a given test description. Generally, files or
directories which will not be modified by the test should be
sym-linked.

If present, "env" must be a dictionary of environment variables and
values. This dictionary will be added to, not replace, the inherited
environment. If an environment variable in "env" was already in the
environment, the value in "env" replaces the old value. This
environment is applied only to the main command.

If "stdout" is not present then the file name for standard output is
constructed from the name of the main command (determined by
"main_command").

If present, "sel_diff_args" must be a dictionary. The keys must be
arguments of the function "selective_diff".

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
line. If two tests have the same title, the last one will be kept.

"""

# Requires Python >= 3.5

import argparse
import datetime
import glob
import json
import os
from os import path
import pathlib
import shutil
import subprocess
import sys
import time

import yachalk

from . import read_runs
from . import compare_single_test
from . import cat_compar


def get_all_required(title, my_run):
    found = True

    for required_type in ["symlink", "copy"]:
        if required_type in my_run:
            assert isinstance(my_run[required_type], list)

            for required_item in my_run[required_type]:
                if isinstance(required_item, list):
                    found = get_single_required(
                        required_item[0],
                        title,
                        my_run,
                        required_item[1],
                        required_type,
                    )
                else:
                    # Wildcards allowed
                    expanded_list = glob.glob(required_item)

                    if len(expanded_list) == 0:
                        print(
                            f"\n{sys.argv[0]}: required {required_item} "
                            "does not exist.\n"
                        )
                        found = False
                    else:
                        for expanded_item in expanded_list:
                            base_dest = path.basename(expanded_item)
                            found = get_single_required(
                                expanded_item,
                                title,
                                my_run,
                                base_dest,
                                required_type,
                            )
                            if not found:
                                break

                if not found:
                    break

            if not found:
                break

    return found


def get_single_required(src, title, my_run, base_dest, required_type):
    """If src exists then symlink or copy src to title/base_dest."""

    found = path.exists(src)

    if found:
        dst = path.join(title, base_dest)

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


def run_single_test(title, my_run, path_failed):
    if "command" in my_run:
        commands = [my_run["command"]]
        main_command = 0
    else:
        commands = my_run["commands"]

        if "main_command" in my_run:
            main_command = my_run["main_command"]
        else:
            main_command = len(commands) - 1

    split_commands = []

    for command in commands:
        if isinstance(command, str):
            command = command.split()

        split_commands.append(command)

    commands = split_commands

    if "stdout" in my_run:
        stdout_filename = my_run["stdout"]
    else:
        stdout_filename = commands[main_command][0]
        stdout_filename = path.basename(stdout_filename)
        stdout_filename = path.splitext(stdout_filename)[0] + "_stdout.txt"

    stderr_filename = stdout_filename.replace("_stdout.txt", "_stderr.txt")

    if "stdin_filename" in my_run and "input" in my_run:
        print(title, ": stdin_filename and input are exclusive.")
        shutil.rmtree(title)
        sys.exit(1)

    os.chdir(title)

    if "create_file" in my_run:
        assert isinstance(my_run["create_file"], list)

        with open(my_run["create_file"][0], "w") as f:
            f.write(my_run["create_file"][1])

    other_kwargs = {}

    if "stdin_filename" in my_run:
        try:
            other_kwargs["stdin"] = open(my_run["stdin_filename"])
        except FileNotFoundError:
            os.chdir("..")
            shutil.rmtree(title)
            raise
    elif "input" in my_run:
        other_kwargs["input"] = my_run["input"]
    else:
        other_kwargs["stdin"] = subprocess.DEVNULL

    if "env" in my_run:
        other_kwargs["env"] = dict(os.environ, **my_run["env"])

    with open("test.json", "w") as f:
        json.dump(my_run, f, indent=3, sort_keys=True)
        f.write("\n")

    t0 = time.perf_counter()

    with open(stdout_filename, "a") as stdout, open(
        stderr_filename, "a"
    ) as stderr:
        for command in commands[:main_command]:
            subprocess.run(
                command,
                check=True,
                stdout=stdout,
                stderr=stderr,
                universal_newlines=True,
            )
            stdout.flush()

        comp_proc = subprocess.run(
            commands[main_command],
            stdout=stdout,
            stderr=stderr,
            universal_newlines=True,
            **other_kwargs,
        )
        stdout.flush()

        if comp_proc.returncode == 0:
            for command in commands[main_command + 1 :]:
                subprocess.run(
                    command,
                    check=True,
                    stdout=stdout,
                    stderr=stderr,
                    universal_newlines=True,
                )
                stdout.flush()

            with open("timing_test_compare.txt", "w") as f:
                t1 = time.perf_counter()
                line = "Elapsed time for test: {:.0f} s\n".format(t1 - t0)
                f.write(line)

            os.chdir("..")
        else:
            os.chdir("..")
            path_failed.touch()
            print(yachalk.chalk.red("failed"))

    return comp_proc.returncode


def run_tests(my_runs, allowed_keys, compare_dir):
    """my_runs should be a dictionary of dictionaries. allowed_keys should
    be a set.

    """

    print("Starting runs at", datetime.datetime.now())
    t0 = time.perf_counter()
    n_failed = 0
    cumul_return = 0
    n_missing = 0

    for i, title in enumerate(my_runs):
        my_run = my_runs[title]
        print(i, end=": ")
        path_failed = pathlib.Path(title, "failed")
        previous_failed = path_failed.exists()

        if path.exists(title) and not previous_failed:
            print("Skipping", title, "(already exists, did not fail)")
            fname = path.join(title, "comparison.txt")

            if path.exists(fname):
                cumul_return += 1
                print("difference found")
        else:
            if not set(my_run) <= allowed_keys:
                print(f"bad keys in {title}:")
                print(set(my_run) - allowed_keys)
                sys.exit(1)

            if previous_failed:
                print("Replacing", title, "because previous run failed...")
                shutil.rmtree(title)
            else:
                print("Creating", title + "...", flush=True)

            os.mkdir(title)
            found = get_all_required(title, my_run)

            if found:
                return_code = run_single_test(title, my_run, path_failed)

                if return_code == 0:
                    old_dir = path.join(compare_dir, title)

                    try:
                        shutil.copytree(title, old_dir, symlinks=True)
                    except FileExistsError:
                        if "sel_diff_args" in my_run:
                            sel_diff_args = my_run["sel_diff_args"]
                        else:
                            sel_diff_args = None

                        return_code = compare_single_test.compare_single_test(
                            title, compare_dir, sel_diff_args
                        )

                        if return_code != 0:
                            print("difference found")
                            cumul_return += 1
                    else:
                        print("Archived", title)
                else:
                    n_failed += 1
            else:
                n_missing += 1
                shutil.rmtree(title)

    print("Elapsed time:", time.perf_counter() - t0, "s")
    print("Number of failed runs:", n_failed)
    print("Number of successful runs with different results:", cumul_return)

    if n_missing != 0:
        print("Number not created because of missing requirements:", n_missing)

    return cumul_return


def main_cli():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "compare_dir",
        help="Directory containing old runs for comparison, after running the "
        "tests",
    )
    parser.add_argument(
        "test_descr",
        nargs="+",
        help="JSON file containing description of tests",
    )
    parser.add_argument(
        "-s",
        "--substitutions",
        help="JSON input file containing " "abbreviations for directory names",
    )
    parser.add_argument(
        "--clean",
        help="""
    Remove any existing run directories in the current directory. With -t,
    remove only the selected run directories, if they exist.""",
        action="store_true",
    )
    parser.add_argument(
        "-l", "--list", help="just list the titles", action="store_true"
    )
    parser.add_argument(
        "-t", "--title", nargs="+", help="select titles in JSON file"
    )
    parser.add_argument(
        "--cat", help="cat files comparison.txt", metavar="FILE"
    )
    args = parser.parse_args()
    my_runs = read_runs.read_runs(args.test_descr)

    if args.list:
        for title in my_runs:
            print(title)
    else:
        my_runs = read_runs.subst_runs(
            my_runs, args.compare_dir, args.substitutions
        )

        if args.title:
            selected_runs = {}

            for t in args.title:
                try:
                    selected_runs[t] = my_runs[t]
                except KeyError:
                    sys.exit(t + " is not a title in the JSON input file.")

            my_runs = selected_runs

        print("Number of runs:", len(my_runs))

        if args.clean:
            for title in my_runs:
                if path.exists(title):
                    print("Removing", title + "...")
                    shutil.rmtree(title)
        else:
            allowed_keys = {
                "command",
                "commands",
                "main_command",
                "description",
                "stdout",
                "symlink",
                "copy",
                "env",
                "stdin_filename",
                "input",
                "test_series_file",
                "create_file",
                "sel_diff_args",
            }
            run_again = True

            while run_again:
                cumul_return = run_tests(
                    my_runs, allowed_keys, args.compare_dir
                )

                if args.cat:
                    cat_compar.cat_compar(args.cat, list(my_runs))

                if cumul_return == 0:
                    run_again = False
                else:
                    reply = input("Replace old runs with difference? ")
                    reply = reply.casefold()
                    run_again = reply.startswith("y")

                    if run_again:
                        print()
                        for title in my_runs:
                            if (
                                path.exists(title)
                                and not pathlib.Path(title, "failed").exists()
                            ):
                                fname = path.join(title, "comparison.txt")

                                if path.exists(fname):
                                    print("Replacing", title)
                                    old_dir = path.join(args.compare_dir, title)

                                    if path.exists(old_dir):
                                        shutil.rmtree(old_dir)

                                    os.remove(fname)

                                    for dirpath, dirnames, filenames in os.walk(
                                        title
                                    ):
                                        if "diff_image.png" in filenames:
                                            os.remove(
                                                path.join(
                                                    dirpath, "diff_image.png"
                                                )
                                            )

                                    shutil.move(title, old_dir)

            reply = input("Remove new runs? ")
            reply = reply.casefold()

            if reply.startswith("y"):
                for title in my_runs:
                    try:
                        shutil.rmtree(title)
                    except FileNotFoundError:
                        pass
