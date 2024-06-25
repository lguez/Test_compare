from os import path
import sys
import json
import os
import tempfile
import string


def read_runs(compare_dir, subst_fname, test_descr_flist):
    my_runs = {}

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

    for test_descr in test_descr_flist:
        try:
            input_file = open(test_descr)
        except FileNotFoundError:
            print("Skipping", test_descr, ", not found")
        else:
            with tempfile.TemporaryFile(mode="w+") as json_substituted:
                for line in input_file:
                    line = string.Template(line).substitute(substitutions)
                    json_substituted.write(line)

                json_substituted.seek(0)
                series = json.load(json_substituted)

            input_file.close()

            for my_run in series.values():
                my_run["test_series_file"] = path.abspath(test_descr)

            my_runs.update(series)

    return my_runs
