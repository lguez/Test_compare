import datetime
import time
from os import path
import pathlib
import argparse

from . import selective_diff
from . import read_runs
from . import compare_single_test
from . import cat_compar


def main_cli():
    parser = argparse.ArgumentParser()
    selective_diff.add_options(parser)
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
        "--cat", help="cat files comparison.txt", metavar="FILE"
    )
    args = parser.parse_args()
    my_runs = read_runs.read_runs(args.test_descr)
    print("Number of runs:", len(my_runs))
    print("Starting comparisons at", datetime.datetime.now())
    t0 = time.perf_counter()
    cumul_return = 0
    sel_diff_args_merge = vars(args).copy()

    for x in ["compare_dir", "test_descr", "cat"]:
        del sel_diff_args_merge[x]

    for i, title in enumerate(my_runs):
        print(f"{i}: {title}")

        if path.exists(title) and not pathlib.Path(title, "failed").exists():
            old_dir = path.join(args.compare_dir, title)

            if path.exists(old_dir):
                # Merge options for selective_diff from the command
                # line with options from the test description, giving
                # priority to the command line:
                if "sel_diff_args" in my_runs[title]:
                    for k, v in my_runs[title]["sel_diff_args"].items():
                        if k in sel_diff_args_merge:
                            if (
                                isinstance(v, list)
                                and sel_diff_args_merge[k] is not None
                            ):
                                sel_diff_args_merge[k] += v
                            else:
                                sel_diff_args_merge[k] = v
                        else:
                            sys.exit(
                                f"Found {k} in sel_diff_args in test "
                                "description, not known in selective_diff"
                            )

                return_code = compare_single_test.compare_single_test(
                    title, args.compare_dir, sel_diff_args_merge
                )

                if return_code != 0:
                    print("difference found")
                    cumul_return += 1
            else:
                print(old_dir, "does not exist")
        else:
            print("Does not exist or failed")

    if args.cat:
        cat_compar.cat_compar(args.cat, list(my_runs))

    print("Elapsed time:", time.perf_counter() - t0, "s")
    print("Number of successful runs with different results:", cumul_return)
