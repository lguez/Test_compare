import time
from os import path
import os
import sys

from . import selective_diff


def compare_single_test(
    title, run_sel_diff_args, compare_dir, sel_diff_args=None
):
    t0 = time.perf_counter()
    old_dir = path.join(compare_dir, title)

    if sel_diff_args is None:
        sel_diff_args = {"exclude": []}
    else:
        sel_diff_args = {"exclude": []} | sel_diff_args

    if run_sel_diff_args is not None:
        sel_diff_args |= run_sel_diff_args

    sel_diff_args["exclude"] = sel_diff_args["exclude"][:] + [
        "timing_test_compare.txt",
        "comparison.txt",
    ]
    # (Copy so  we do not modify run_sel_diff_args["exclude"].)

    fname = path.join(title, "comparison.txt")

    with open(fname, "w") as f_obj:
        return_code = selective_diff.selective_diff(
            [old_dir, title], **sel_diff_args, file_out=f_obj
        )
        f_obj.write("\n" + ("*" * 10 + "\n") * 2 + "\n")

    if return_code == 0:
        os.remove(fname)
    elif return_code != 1:
        sys.exit(
            "Problem in selective_diff.py, return code should be 0 or 1.\n"
            'See "comparison.txt".'
        )

    t1 = time.perf_counter()
    line = "Elapsed time for comparison: {:.0f} s\n".format(t1 - t0)
    fname = path.join(title, "timing_test_compare.txt")

    with open(fname, "a") as f_obj:
        f_obj.write(line)

    return return_code
