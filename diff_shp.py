#!/usr/bin/env python3

import itertools
import shapefile
import numpy as np
from matplotlib import pyplot as plt
from shapely import geometry, validation
from os import path
import argparse
import sys

def compare_rings(detail_file, r_old, r_new, marker, i, j, k = None):
    """r_old and r_new are LinearRing objects from the geometry module."""

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

        my_label = str(i)
        if j is not None: my_label = my_label + ", " + str(j)

        if k is None:
            my_label = my_label + " ext"
        else:
            my_label = my_label + " int " + str(k)

        x, y = r_old.xy
        l = plt.plot(x, y, "-o", markersize = 12, fillstyle = "none",
                     label = "old " + my_label)

        x, y = r_new.xy
        plt.plot(x, y, marker = next(marker), label =  "new " + my_label,
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
            detail_file.write(f"old: {validation.explain_validity(r_old)}\n")
            detail_file.write(f"new: {validation.explain_validity(r_new)}\n")

def compare_poly(detail_file, p_old, p_new, marker, i, j = None):
    """
    p_old and p_new are polygon objects from the geometry module.
    i: shape number
    j: polygon number for a multi-polygon
    """

    compare_rings(detail_file, p_old.exterior, p_new.exterior, marker, i, j)

    for k, (r_old, r_new) in enumerate(zip(p_old.interiors, p_new.interiors)):
        compare_rings(detail_file, r_old, r_new, marker, i, j, k)

def diff_shp(old, new, report_identical = False, detail_file = sys.stdout):
    detail_file.write('\n' + "*" * 10 + '\n\n')
    detail_file.write(f"diff {old} {new}\n")
    reader_old = shapefile.Reader(old)
    reader_new = shapefile.Reader(new)
    diff_found = False

    if reader_old.numRecords != reader_new.numRecords:
        diff_found = True
        detail_file.write("Not the same number of records: "
                          f"{reader_old.numRecords} {reader_new.numRecords}\n")
        detail_file.write("Comparing the first "
              f"{min(reader_old.numRecords, reader_new.numRecords)}"
              "records...\n")

    my_figure = plt.figure()
    # (We purposely do not create the axes now because we do not know if
    # we will have something to draw and we want to test the presence of
    # axes at the end of the script.)

    marker = itertools.cycle(["+", "v", "^", "x"])

    print("\n************************")
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
                nparts = len(s_old.parts)

                if nparts != len(s_new.parts):
                    detail_file.write(f"Numbers of parts in shape {i} differ:"
                                      f"{nparts} {len(s_new.parts)}\n")
                else:
                    g_old = geometry.shape(s_old.__geo_interface__)
                    g_new = geometry.shape(s_new.__geo_interface__)

                    if g_old.geom_type == g_new.geom_type:
                        if g_old.geom_type == "MultiPolygon":
                            for j, (p_old, p_new) in enumerate(zip(g_old,
                                                                   g_new)):
                                compare_poly(detail_file, p_old, p_new,
                                             marker, i, j)
                        elif g_old.geom_type == "Polygon":
                            compare_poly(detail_file, g_old, g_new, marker, i)
                        elif g_old.geom_type == "Point":
                            abs_rel_diff = np.abs(np.array(g_new)
                                                  / np.array(g_old) - 1)
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

    if my_figure.axes:
        plt.legend()
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
    args = parser.parse_args()

    if path.isdir(args.new):
        # Assume that basename is the same:
        basename = path.basename(args.old)
        new = path.join(args.new, basename)
    else:
        new = args.new

    ret_code = diff_shp(args.old, new, args.report_identical)
    sys.exit(ret_code)
