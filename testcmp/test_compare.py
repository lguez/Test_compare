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
from importlib import metadata

import yachalk

from testcmp import read_runs
from testcmp import compare_single_test
from testcmp import cat_compar


def get_all_required(title, my_run):
    found = True

    for required_type in ["symlink", "copy"]:
        if required_type in my_run:
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


def run_single_test(title, my_run, path_failed, compare_dir):
    """return_code: 0 means means successful with same result, 1 means
    failed, 2 means successful with different result, 3 means missing
    requirement.

    """

    os.mkdir(title)
    found = get_all_required(title, my_run)

    if found:
        if "main_command" in my_run:
            main_command = my_run["main_command"]
        else:
            main_command = len(my_run["commands"]) - 1

        if "stdout" in my_run:
            stdout_filename = my_run["stdout"]
        else:
            stdout_filename = my_run["commands"][main_command][0]
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

        try:
            with open(stdout_filename, "a") as stdout, open(
                stderr_filename, "a"
            ) as stderr:
                for command in my_run["commands"][:main_command]:
                    subprocess.run(
                        command,
                        check=True,
                        stdout=stdout,
                        stderr=stderr,
                        universal_newlines=True,
                    )
                    stdout.flush()

                subprocess.run(
                    my_run["commands"][main_command],
                    check=True,
                    stdout=stdout,
                    stderr=stderr,
                    universal_newlines=True,
                    **other_kwargs,
                )
                stdout.flush()

                for command in my_run["commands"][main_command + 1 :]:
                    subprocess.run(
                        command,
                        check=True,
                        stdout=stdout,
                        stderr=stderr,
                        universal_newlines=True,
                    )
                    stdout.flush()
        except subprocess.CalledProcessError:
            os.chdir("..")
            path_failed.touch()
            print(yachalk.chalk.red("failed"))
            return_code = 1
        else:
            t1 = time.perf_counter()
            line = "Elapsed time for test: {:.0f} s\n".format(t1 - t0)

            with open("timing_test_compare.txt", "w") as f_obj:
                f_obj.write(line)

            os.chdir("..")
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
                    print(yachalk.chalk.blue("difference found"))
                    return_code = 2
            else:
                print("Archived", title)
                return_code = 0
    else:
        return_code = 3
        shutil.rmtree(title)

    return return_code


def dependencies_exist(dependencies, compare_dir):
    for title in dependencies:
        old_dir = path.join(compare_dir, title)

        if not path.isdir(old_dir):
            return_value = False
            break
    else:
        return_value = True

    return return_value


def run_tests(my_runs, compare_dir, verbose):
    """my_runs should be a dictionary of dictionaries."""

    print("Starting runs at", datetime.datetime.now())
    t0 = time.perf_counter()
    n_failed = 0
    n_diff = 0
    n_missing = 0

    for i, title in enumerate(my_runs):
        my_run = my_runs[title]
        path_failed = pathlib.Path(title, "failed")
        previous_failed = path_failed.exists()

        if path.exists(title) and not previous_failed:
            fname = path.join(title, "comparison.txt")

            if path.exists(fname):
                if verbose:
                    print(
                        f"{i}: Skipping",
                        title,
                        "(already exists, did not fail)",
                    )
                    print(yachalk.chalk.blue("difference found"))

                n_diff += 1
            else:
                if not dependencies_exist(my_run["dependencies"], compare_dir):
                    n_missing += 1

                    if verbose:
                        print(f"{i}: Skipping", title)
                        print(
                            "(already exists, did not fail, no difference, "
                            "missing dependencies)"
                        )
                else:
                    for d in my_run["dependencies"]:
                        old_dir = path.join(compare_dir, d)

                        if path.getmtime(old_dir) > path.getmtime(title):
                            need_update = True
                            break
                    else:
                        need_update = False

                    if need_update:
                        print(f"{i}: Replacing", title, "because outdated...")
                        shutil.rmtree(title)
                        return_code = run_single_test(
                            title, my_run, path_failed, compare_dir
                        )

                        if return_code == 1:
                            n_failed += 1
                        elif return_code == 2:
                            n_diff += 1
                        elif return_code == 3:
                            n_missing += 1
                    else:
                        if verbose:
                            print(f"{i}: Skipping", title)
                            print(
                                "(already exists, did not fail, no difference, "
                                "no update needed)"
                            )
        else:
            if dependencies_exist(my_run["dependencies"], compare_dir):
                if previous_failed:
                    print(
                        f"{i}: Replacing",
                        title,
                        "because previous run failed...",
                    )
                    shutil.rmtree(title)
                else:
                    print(f"{i}: Creating", title + "...", flush=True)

                return_code = run_single_test(
                    title, my_run, path_failed, compare_dir
                )

                if return_code == 1:
                    n_failed += 1
                elif return_code == 2:
                    n_diff += 1
                elif return_code == 3:
                    n_missing += 1
            else:
                n_missing += 1
                if verbose:
                    print(
                        f"{i}: Skipping",
                        title,
                        "because of missing dependencies",
                    )

    print("Elapsed time:", time.perf_counter() - t0, "s")
    print("Number of failed runs:", n_failed)
    print("Number of successful runs with different results:", n_diff)

    if n_missing != 0:
        print(
            "Number not created because of missing requirements or "
            "dependencies:",
            n_missing,
        )

    return n_diff


def extract_dependency(word, dependencies):
    my_parts = pathlib.Path(word).parts

    try:
        i = my_parts.index("$tests_old_dir")
    except ValueError:
        pass
    else:
        if my_parts[i + 1] not in dependencies:
            dependencies.append(my_parts[i + 1])


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
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--version", action="version", version=metadata.version("testcmp")
    )
    args = parser.parse_args()
    my_runs = read_runs.read_runs(args.test_descr)

    if args.list:
        for title in my_runs:
            print(title)
    else:
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

            for title, my_run in my_runs.items():
                if not set(my_run) <= allowed_keys:
                    print(f"bad keys in {title}:")
                    print(set(my_run) - allowed_keys)
                    sys.exit(1)

            for my_run in my_runs.values():
                if "command" in my_run:
                    my_run["commands"] = [my_run["command"]]
                    del my_run["command"]

                split_commands = []

                for command in my_run["commands"]:
                    if isinstance(command, str):
                        command = command.split()

                    split_commands.append(command)

                my_run["commands"] = split_commands

            for my_run in my_runs.values():
                my_run["dependencies"] = []

                for command in my_run["commands"]:
                    for word in command:
                        extract_dependency(word, my_run["dependencies"])

                for required_type in ["symlink", "copy"]:
                    if required_type in my_run:
                        assert isinstance(my_run[required_type], list)

                        for required_item in my_run[required_type]:
                            if isinstance(required_item, list):
                                extract_dependency(
                                    required_item[0], my_run["dependencies"]
                                )
                            else:
                                extract_dependency(
                                    required_item, my_run["dependencies"]
                                )

            my_runs = read_runs.subst_runs(
                my_runs, args.compare_dir, args.substitutions
            )

            run_again = True

            while run_again:
                n_diff = run_tests(my_runs, args.compare_dir, args.verbose)

                if args.cat:
                    cat_compar.cat_compar(args.cat, list(my_runs))

                if n_diff == 0:
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
