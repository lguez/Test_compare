#!/usr/bin/env python3

import itertools
import shapefile
import numpy as np
from matplotlib import pyplot as plt
from shapely import geometry, validation
from os import path
import argparse
import sys

def compare_rings(r_old, r_new, marker, i, j, k = None):
    """r_old and r_new are LinearRing objects from the geometry module."""

    print("\nShape", i, end = "")
    if j is not None: print(", part", j, end = "")

    if k is None:
        print(", exterior:")
    else:
        print(", interior", k, ":")

    if r_old.equals(r_new):
        print("This is just a difference by permutation or ordering.")
    else:
        len_old = len(r_old.coords)
        len_new = len(r_new.coords)

        if len_new != len_old:
            print("Numbers of points differ:",  len_old, len_new)

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
                print("Area of symmetric difference / area of old shape:",
                      sym_diff.area / pr_old.area)
            else:
                print("Area of old shape is 0. \n"
                      "Note this should never be in a polygon shapefile.")
        else:
            print("Cannot compute symmetric difference.")
            print("old:", validation.explain_validity(r_old))
            print("new:", validation.explain_validity(r_new))

def compare_poly(p_old, p_new, marker, i, j = None):
    """
    p_old and p_new are polygon objects from the geometry module.
    i: shape number
    j: polygon number for a multi-polygon
    """

    compare_rings(p_old.exterior, p_new.exterior, marker, i, j)

    for k, (r_old, r_new) in enumerate(zip(p_old.interiors, p_new.interiors)):
        compare_rings(r_old, r_new, marker, i, j, k)

def diff_shp(old, new, report_identical = False, detail_file = sys.stdout):
    reader_old = shapefile.Reader(old)
    reader_new = shapefile.Reader(new)
    diff_found = False

    if reader_old.numRecords != reader_new.numRecords:
        diff_found = True
        print("Not the same number of records:", reader_old.numRecords,
              reader_new.numRecords)
        print("Comparing the first",
              min(reader_old.numRecords, reader_new.numRecords),
              "records...")

    my_figure = plt.figure()
    # (We purposely do not create the axes now because we do not know if
    # we will have something to draw and we want to test the presence of
    # axes at the end of the script.)

    marker = itertools.cycle(["+", "v", "^", "x"])

    print("\n************************")
    print("Difference in vertices:")

    for i, (s_old, s_new) in enumerate(zip(reader_old.iterShapes(),
                                           reader_new.iterShapes())):
        if s_old.points == s_new.points:
            if report_identical:
                print("\nVertices for shape", i, "are identical.")
        else:
            diff_found = True
            print("\nVertices for shape", i, "differ.")

            if s_old.shapeType == shapefile.NULL:
                print("Old shape is NULL.")
            elif s_new.shapeType == shapefile.NULL:
                print("New shape is NULL.")
            else:
                nparts = len(s_old.parts)

                if nparts != len(s_new.parts):
                    print("Numbers of parts in shape", i, "differ:", nparts,
                          len(s_new.parts))
                else:
                    g_old = geometry.shape(s_old.__geo_interface__)
                    g_new = geometry.shape(s_new.__geo_interface__)

                    if g_old.geom_type == g_new.geom_type:
                        if g_old.geom_type == "MultiPolygon":
                            for j, (p_old, p_new) in enumerate(zip(g_old,
                                                                   g_new)):
                                compare_poly(p_old, p_new, marker, i, j)
                        elif g_old.geom_type == "Polygon":
                            compare_poly(g_old, g_new, marker, i)
                        elif g_old.geom_type == "Point":
                            print("Absolute value of relative difference:",
                                  np.abs(np.array(g_new) / np.array(g_old) - 1))
                        else:
                            print("Geometry type not supported:",
                                  g_old.geom_type)
                    else:
                        print("Geometry types differ:", g_old.geom_type,
                              g_new.geom_type)

    if my_figure.axes:
        plt.legend()
        plt.show()

    return diff_found

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

    diff_found = diff_shp(args.old, new, args.report_identical)
    if diff_found: sys.exit(1)
