#!/usr/bin/env python3

import itertools
from os import path
import argparse
import sys

import shapefile
import numpy as np
from matplotlib import pyplot as plt





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

    for i, (s_old, s_new) in enumerate(
        zip(reader_old.iterShapes(), reader_new.iterShapes())
    ):
        if s_old.points == s_new.points:
            if report_identical:
                detail_file.write(f"\nVertices for shape {i} are identical.\n")
        else:
            diff_found = True
            detail_file.write(f"\nVertices for shape {i} differ.\n")

            if s_old.shapeType == shapefile.NULL:
                detail_file.write("Old shape is NULL.\n")
            elif s_new.shapeType == shapefile.NULL:
                detail_file.write("New shape is NULL.\n")
            else:
                nparts_old = len(s_old.parts)
                nparts_new = len(s_new.parts)

                if nparts_old != nparts_new:
                    detail_file.write(
                        f"Numbers of parts in shape {i} differ:"
                        f"{nparts_old} {nparts_new}\n"
                    )
                else:
                    if len(s_old.points) == 0:
                        detail_file.write(f"No point in old shape {i}\n")
                    elif len(s_new.points) == 0:
                        detail_file.write(f"No point in new shape {i}\n")
                    else:
                        # Suppress possible warning about orientation
                        # of polygon (only is effective with version
                        # >= 2.2.0 of pyshp):
                        shapefile.VERBOSE = False

                        g_old = geometry.shape(s_old.__geo_interface__)
                        g_new = geometry.shape(s_new.__geo_interface__)
                        shapefile.VERBOSE = True

                        if g_old.geom_type == g_new.geom_type:
                            if g_old.geom_type == "MultiPolygon":
                                for j, (p_old, p_new) in enumerate(
                                    zip(g_old, g_new)
                                ):
                                    compare_poly(
                                        ax,
                                        p_old,
                                        p_new,
                                        i,
                                        j,
                                        detail_file,
                                        marker_iter,
                                        tolerance,
                                    )
                            elif g_old.geom_type == "Polygon":
                                compare_poly(
                                    ax,
                                    g_old,
                                    g_new,
                                    i,
                                    detail_file=detail_file,
                                    marker_iter=marker_iter,
                                    tolerance=tolerance,
                                )
                            elif g_old.geom_type == "Point":
                                abs_rel_diff = np.abs(
                                    np.array(g_new.coords)
                                    / np.array(g_old.coords)
                                    - 1
                                )
                                detail_file.write(
                                    "Absolute value of relative difference: "
                                    f"{abs_rel_diff}\n"
                                )
                            else:
                                detail_file.write(
                                    "Geometry type not supported:"
                                    f"{g_old.geom_type}\n"
                                )
                        else:
                            detail_file.write(
                                "Geometry types differ:"
                                f"{g_old.geom_type} {g_new.geom_type}\n"
                            )

    detail_file.write("\n")

    if plot:
        ax.legend()
        plt.show()

    if diff_found:
        return 1
    else:
        return 0


if __name__ == "__main__":
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
        help="maximum relative error for comparison of area of symmetric difference",
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
