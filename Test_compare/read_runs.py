from os import path
import sys
import json
import os
import tempfile
import string


def read_runs(test_descr_flist):
    my_runs = {}

    for test_descr in test_descr_flist:
        try:
            input_file = open(test_descr)
        except FileNotFoundError:
            print("Skipping", test_descr, ", not found")
        else:
            series = json.load(input_file)
            input_file.close()

            for my_run in series.values():
                my_run["test_series_file"] = path.abspath(test_descr)

            my_runs.update(series)

    return my_runs


def subst_runs(my_runs, compare_dir, subst_fname=None):
    if not path.isdir(compare_dir):
        sys.exit("Directory " + compare_dir + " not found.")

    if subst_fname:
        with open(subst_fname) as subst_file:
            substitutions = json.load(subst_file)

        assert "PWD" not in substitutions
        assert "tests_old_dir" not in substitutions
    else:
        substitutions = {}

    substitutions["PWD"] = os.getcwd()
    substitutions["tests_old_dir"] = path.abspath(compare_dir)
    my_runs_dump = json.dumps(my_runs)
    my_runs_substituted = string.Template(my_runs_dump).substitute(
        substitutions
    )
    return json.loads(my_runs_substituted)
