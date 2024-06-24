#!/usr/bin/env python3

import itertools
import sys

import shapefile
from matplotlib import pyplot as plt

import diff_shapes


def diff_shp(
    old,
    new,
    report_identical=False,
    plot=False,
    detail_file=sys.stdout,
    tolerance=0.0,
):
    detail_file.write("\n" + "*" * 10 + "\n\n")
    detail_file.write(f"diff {old} {new}\n")
    reader_old = shapefile.Reader(old)
    reader_new = shapefile.Reader(new)
    diff_found = False

    if reader_old.numRecords != reader_new.numRecords:
        diff_found = True
        detail_file.write(
            "Not the same number of records: "
            f"{reader_old.numRecords} {reader_new.numRecords}\n"
        )
        n_rec = min(reader_old.numRecords, reader_new.numRecords)
        detail_file.write(f"Comparing the first {n_rec} records...\n")

    if plot:
        fig, ax = plt.subplots()
        marker_iter = itertools.cycle(["+", "v", "^", "x"])
    else:
        ax = None
        marker_iter = itertools.repeat(None)

    detail_file.write("Difference in vertices:\n")
    ret_code = 0

    for i_shape, (s_old, s_new) in enumerate(
        zip(reader_old.iterShapes(), reader_new.iterShapes())
    ):
        ret_code += diff_shapes.diff_shapes(
            s_old,
            s_new,
            report_identical,
            detail_file,
            i_shape,
            ax,
            marker_iter,
            tolerance,
        )

    diff_found = diff_found or ret_code != 0
    detail_file.write("\n")

    if plot:
        ax.legend()
        plt.show()

    return 1 if diff_found else 0


if __name__ == "__main__":
    from os import path
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("old", help="shapefile")
    parser.add_argument("new", help="shapefile or directory")
    parser.add_argument(
        "-s",
        "--report-identical",
        action="store_true",
        help="report when vertices are the same",
    )
    parser.add_argument("-p", "--plot", action="store_true")
    parser.add_argument(
        "-t",
        "--tolerance",
        default=0.0,
        type=float,
        help="maximum relative error for comparison of area of symmetric "
        "difference (default 0.)",
    )
    args = parser.parse_args()

    if path.isdir(args.new):
        # Assume that basename is the same:
        basename = path.basename(args.old)
        new = path.join(args.new, basename)
    else:
        new = args.new

    ret_code = diff_shp(
        args.old,
        new,
        args.report_identical,
        args.plot,
        tolerance=args.tolerance,
    )
    sys.exit(ret_code)
