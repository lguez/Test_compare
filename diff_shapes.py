import io

import shapefile
from shapely import geometry
import numpy as np

import compare_poly


def diff_shapes(
    s_old,
    s_new,
    report_identical,
    detail_file,
    i_shape,
    ax,
    marker_iter,
    tolerance,
):
    if s_old.points == s_new.points:
        diff_found = False

        if report_identical:
            detail_file.write(
                f"\nVertices for shape {i_shape} are identical.\n"
            )
    else:
        detail_subfile = io.StringIO()
        detail_subfile.write(f"\nVertices for shape {i_shape} differ.\n")

        if s_old.shapeType == shapefile.NULL:
            diff_found = True
            detail_subfile.write("Old shape is NULL.\n")
        elif s_new.shapeType == shapefile.NULL:
            diff_found = True
            detail_subfile.write("New shape is NULL.\n")
        else:
            nparts_old = len(s_old.parts)
            nparts_new = len(s_new.parts)

            if nparts_old != nparts_new:
                diff_found = True
                detail_subfile.write(
                    f"Numbers of parts in shape {i_shape} differ:"
                    f"{nparts_old} {nparts_new}\n"
                )
            else:
                if len(s_old.points) == 0:
                    diff_found = True
                    detail_subfile.write(f"No point in old shape {i_shape}\n")
                elif len(s_new.points) == 0:
                    diff_found = True
                    detail_subfile.write(f"No point in new shape {i_shape}\n")
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
                            ret_code = 0

                            for j, (p_old, p_new) in enumerate(
                                zip(g_old, g_new)
                            ):
                                ret_code += compare_poly.compare_poly(
                                    ax,
                                    p_old,
                                    p_new,
                                    i_shape,
                                    j,
                                    detail_subfile,
                                    marker_iter,
                                    tolerance,
                                    report_identical,
                                )

                            diff_found = ret_code != 0
                        elif g_old.geom_type == "Polygon":
                            ret_code = compare_poly.compare_poly(
                                ax,
                                g_old,
                                g_new,
                                i_shape,
                                detail_file=detail_subfile,
                                marker_iter=marker_iter,
                                tolerance=tolerance,
                                report_identical=report_identical,
                            )
                            diff_found = ret_code != 0
                        elif g_old.geom_type == "Point":
                            abs_rel_diff = np.abs(
                                np.array(g_new.coords) / np.array(g_old.coords)
                                - 1
                            )
                            diff_found = abs_rel_diff > tolerance
                            detail_subfile.write(
                                "Absolute value of relative difference: "
                                f"{abs_rel_diff}\n"
                            )
                        else:
                            diff_found = True
                            detail_subfile.write(
                                "Geometry type not supported:"
                                f"{g_old.geom_type}\n"
                            )
                    else:
                        diff_found = True
                        detail_subfile.write(
                            "Geometry types differ:"
                            f"{g_old.geom_type} {g_new.geom_type}\n"
                        )

        if diff_found or report_identical:
            detail_diag = detail_subfile.getvalue()
            detail_file.write(detail_diag)

    return 1 if diff_found else 0
