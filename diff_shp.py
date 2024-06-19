#!/usr/bin/env python3

import itertools
from os import path
import argparse
import sys

import shapefile
import numpy as np
from matplotlib import pyplot as plt
from shapely import geometry, validation

def compare_rings(ax, detail_file, r_old, r_new, marker, i, j, k = None):
    """r_old and r_new are LinearRing objects from the geometry
    module. marker is not used if ax is none.

    """

    detail_file.write(f"\nShape {i}")
    if j is not None: detail_file.write(f", part {j}")

    if k is None:
        detail_file.write(", exterior:\n")
    else:
        detail_file.write(f", interior {k}:\n")

    if r_old.equals(r_new):
        detail_file.write("This is just a difference by permutation or "
                          "ordering.\n")
    else:
        len_old = len(r_old.coords)
        len_new = len(r_new.coords)

        if len_new != len_old:
            detail_file.write(f"Numbers of points differ: {len_old} "
                              f"{len_new}\n")

        if ax:
            my_label = str(i)
            if j is not None: my_label = my_label + ", " + str(j)

            if k is None:
                my_label = my_label + " ext"
            else:
                my_label = my_label + " int " + str(k)

            x, y = r_old.xy
            l = ax.plot(x, y, "-o", markersize = 12, fillstyle = "none",
                        label = "old " + my_label)

            x, y = r_new.xy
            ax.plot(x, y, marker = marker, label =  "new " + my_label,
                    color = l[0].get_color())

        if r_old.is_valid and r_new.is_valid:
            pr_old = geometry.Polygon(r_old)
            pr_new = geometry.Polygon(r_new)
            sym_diff = pr_new.symmetric_difference(pr_old)
            if pr_old.area != 0:
                detail_file.write("Area of symmetric difference / area of old "
                                  f"shape: {sym_diff.area / pr_old.area}\n")
            else:
                detail_file.write("Area of old shape is 0. \n"
                      "Note this should never be in a polygon shapefile.\n")
        else:
            detail_file.write("Cannot compute symmetric difference.\n")
            explain = validation.explain_validity(r_old)
            detail_file.write(f"old: {explain}\n")
            explain = validation.explain_validity(r_new)
            detail_file.write(f"new: {explain}\n")

def compare_poly(ax, p_old, p_new, i, j = None,
                 detail_file = sys.stdout,
                 marker_iter = itertools.repeat(None)):
    """p_old and p_new are polygon objects from the geometry module. i:
    shape number j: polygon number for a multi-polygon. If ax is equal
    to None then we do not plot, so we do not set a default value for
    ax.

    """

    compare_rings(ax, detail_file, p_old.exterior, p_new.exterior,
                  next(marker_iter), i, j)

    for k, (r_old, r_new) in enumerate(zip(p_old.interiors, p_new.interiors)):
        compare_rings(ax, detail_file, r_old, r_new, next(marker_iter), i, j, k)

def diff_shp(old, new, report_identical = False, plot = False,
             detail_file = sys.stdout):
    detail_file.write('\n' + "*" * 10 + '\n\n')
    detail_file.write(f"diff {old} {new}\n")
    reader_old = shapefile.Reader(old)
    reader_new = shapefile.Reader(new)
    diff_found = False

    if reader_old.numRecords != reader_new.numRecords:
        diff_found = True
        detail_file.write("Not the same number of records: "
                          f"{reader_old.numRecords} {reader_new.numRecords}\n")
        n_rec = min(reader_old.numRecords, reader_new.numRecords)
        detail_file.write(f"Comparing the first {n_rec} records...\n")

    if plot:
        fig, ax = plt.subplots()
        marker_iter = itertools.cycle(["+", "v", "^", "x"])
    else:
        ax = None
        marker_iter = itertools.repeat(None)

    detail_file.write("Difference in vertices:\n")

    for i, (s_old, s_new) in enumerate(zip(reader_old.iterShapes(),
                                           reader_new.iterShapes())):
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
                    detail_file.write(f"Numbers of parts in shape {i} differ:"
                                      f"{nparts_old} {nparts_new}\n")
                else:
                    # Suppress possible warning about orientation of polygon:
                    shapefile.VERBOSE = False

                    g_old = geometry.shape(s_old.__geo_interface__)
                    g_new = geometry.shape(s_new.__geo_interface__)
                    shapefile.VERBOSE = True

                    if g_old.geom_type == g_new.geom_type:
                        if g_old.geom_type == "MultiPolygon":
                            for j, (p_old, p_new) in enumerate(zip(g_old,
                                                                   g_new)):
                                compare_poly(ax, p_old, p_new, i, j,
                                             detail_file, marker_iter)
                        elif g_old.geom_type == "Polygon":
                            compare_poly(ax, g_old, g_new, i,
                                         detail_file = detail_file,
                                         marker_iter = marker_iter)
                        elif g_old.geom_type == "Point":
                            abs_rel_diff = np.abs(np.array(g_new.coords)
                                                  / np.array(g_old.coords) - 1)
                            detail_file.write\
                                ("Absolute value of relative difference: "
                                 f"{abs_rel_diff}\n")
                        else:
                            detail_file.write("Geometry type not supported:"
                                              f"{g_old.geom_type}\n")
                    else:
                        detail_file.write("Geometry types differ:"
                                          f"{g_old.geom_type}"
                                          f"{g_new.geom_type}\n")

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
    parser.add_argument("old", help = "shapefile")
    parser.add_argument("new", help = "shapefile or directory")
    parser.add_argument("-s", "--report-identical", action = "store_true",
                        help = "report when vertices are the same")
    parser.add_argument("-p", "--plot", action = "store_true")
    args = parser.parse_args()

    if path.isdir(args.new):
        # Assume that basename is the same:
        basename = path.basename(args.old)
        new = path.join(args.new, basename)
    else:
        new = args.new

    ret_code = diff_shp(args.old, new, args.report_identical, args.plot)
    sys.exit(ret_code)
