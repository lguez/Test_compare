import itertools
import sys
import io

from shapely import geometry, validation


def compare_rings(
    ax,
    detail_file,
    r_old,
    r_new,
    marker,
    i,
    j,
    k=None,
    tolerance=0.0,
    report_identical=False,
):
    """r_old and r_new are LinearRing objects from the geometry
    module. marker is not used if ax is None.

    """

    # We need to insert a header before detailed diagnostic, but only
    # if we find differences, so create a new text stream:
    detail_subfile = io.StringIO()

    detail_subfile.write(f"\nShape {i}")
    if j is not None:
        detail_subfile.write(f", part {j}")

    if k is None:
        detail_subfile.write(", exterior:\n")
    else:
        detail_subfile.write(f", interior {k}:\n")

    if r_old.equals(r_new):
        if report_identical:
            detail_subfile.write(
                "This is just a difference by permutation or ordering.\n"
            )

        diff_found = False
    else:
        len_old = len(r_old.coords)
        len_new = len(r_new.coords)

        if len_new != len_old:
            if report_identical:
                detail_subfile.write(
                    f"Numbers of points differ: {len_old} {len_new}\n"
                )

        if ax:
            my_label = str(i)
            if j is not None:
                my_label = my_label + ", " + str(j)

            if k is None:
                my_label = my_label + " ext"
            else:
                my_label = my_label + " int " + str(k)

            x, y = r_old.xy
            l = ax.plot(
                x,
                y,
                "-o",
                markersize=12,
                fillstyle="none",
                label="old " + my_label,
            )

            x, y = r_new.xy
            ax.plot(
                x,
                y,
                marker=marker,
                label="new " + my_label,
                color=l[0].get_color(),
            )

        if r_old.is_valid and r_new.is_valid:
            pr_old = geometry.Polygon(r_old)
            pr_new = geometry.Polygon(r_new)
            sym_diff = pr_new.symmetric_difference(pr_old)
            if pr_old.area != 0:
                my_diff = sym_diff.area / pr_old.area

                if my_diff <= tolerance:
                    if report_identical:
                        detail_subfile.write("Negligible difference\n")

                    diff_found = False
                else:
                    detail_subfile.write(
                        "Area of symmetric difference / area of old "
                        f"shape: {my_diff}\n"
                    )
                    diff_found = True
            else:
                detail_subfile.write(
                    "Area of old shape is 0. \n"
                    "Note this should never be in a polygon shapefile.\n"
                )
                diff_found = True
        else:
            detail_subfile.write("Cannot compute symmetric difference.\n")
            explain = validation.explain_validity(r_old)
            detail_subfile.write(f"old: {explain}\n")
            explain = validation.explain_validity(r_new)
            detail_subfile.write(f"new: {explain}\n")
            diff_found = True

    if diff_found or report_identical:
        detail_diag = detail_subfile.getvalue()
        detail_file.write(detail_diag)



def compare_poly(
    ax,
    p_old,
    p_new,
    i,
    j=None,
    detail_file=sys.stdout,
    marker_iter=itertools.repeat(None),
    tolerance=0.0,
    report_identical=False,
):
    """p_old and p_new are polygon objects from the geometry module. i:
    shape number j: polygon number for a multi-polygon. If ax is equal
    to None then we do not plot, so we do not set a default value for
    ax.

    """

    compare_rings(
        ax,
        detail_file,
        p_old.exterior,
        p_new.exterior,
        next(marker_iter),
        i,
        j,
        tolerance=tolerance,
        report_identical=report_identical,
    )

    for k, (r_old, r_new) in enumerate(zip(p_old.interiors, p_new.interiors)):
        compare_rings(
            ax,
            detail_file,
            r_old,
            r_new,
            next(marker_iter),
            i,
            j,
            k,
            tolerance,
            report_identical,
        )
