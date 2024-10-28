#!/usr/bin/env python3

import shapefile
import numpy as np
from os import path


def diff_dbf(old, new, report_identical=False, quiet=False):
    """old is the path to a shapefile. new may be the path to a shapefile
    or to a directory containing a shapefile.

    """

    if path.isdir(new):
        # Assume that basename is the same:
        basename = path.basename(old)
        new = path.join(new, basename)
    else:
        new = new

    reader_old = shapefile.Reader(old)
    reader_new = shapefile.Reader(new)
    diff_found = False

    if reader_old.numRecords != reader_new.numRecords:
        diff_found = True

        if not quiet:
            print(
                "Not the same number of records:",
                reader_old.numRecords,
                reader_new.numRecords,
            )
            print(
                "Comparing the first",
                min(reader_old.numRecords, reader_new.numRecords),
                "records...",
            )

    if reader_old.fields == reader_new.fields:
        max_diff = 0.0

        for i, (r_old, r_new) in enumerate(
            zip(reader_old.iterRecords(), reader_new.iterRecords())
        ):
            if r_new == r_old:
                if report_identical:
                    print("\nAttributes for shape", i, "are identical.")
            else:
                diff_found = True

                if not quiet:
                    current_diff = abs(np.array(r_new) / np.array(r_old) - 1)
                    # (Note that a mixture of int and float in a record
                    # will create a float array.)

                    print(
                        "\nAttributes for shape",
                        i,
                        "differ. Absolute value of relative difference:",
                    )
                    print(current_diff)
                    max_diff = np.maximum(max_diff, current_diff)

        if not quiet and diff_found:
            print("Indices above are 0-based.\n")
            print("Maximum over all records:", max_diff)
    else:
        diff_found = True

        if not quiet:
            print("Not the same fields:")
            print("Old fields:", reader_old.fields[1:])
            print("New fields:", reader_new.fields[1:])

    if diff_found:
        return 1
    else:
        return 0


def main_cli():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("old", help="dbf-file")
    parser.add_argument("new", help="dbf-file or directory")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-s",
        "--report-identical",
        action="store_true",
        help="report when attributes are the same",
    )
    group.add_argument(
        "-q", "--quiet", action="store_true", help="suppress all normal output"
    )
    args = parser.parse_args()

    return_diff_dbf = diff_dbf(
        args.old, args.new, args.report_identical, args.quiet
    )
    sys.exit(return_diff_dbf)
