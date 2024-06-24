import itertools
import sys

from shapely import geometry, validation


def compare_rings(
    ax, detail_file, r_old, r_new, marker, i, j, k=None, tolerance=0.0
):
    """r_old and r_new are LinearRing objects from the geometry
    module. marker is not used if ax is None.

    """

    detail_file.write(f"\nShape {i}")
    if j is not None:
        detail_file.write(f", part {j}")

    if k is None:
        detail_file.write(", exterior:\n")
    else:
        detail_file.write(f", interior {k}:\n")

    if r_old.equals(r_new):
        detail_file.write(
            "This is just a difference by permutation or ordering.\n"
        )
    else:
        len_old = len(r_old.coords)
        len_new = len(r_new.coords)

        if len_new != len_old:
            detail_file.write(
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
                    detail_file.write("Negligible difference\n")
                else:
                    detail_file.write(
                        "Area of symmetric difference / area of old "
                        f"shape: {my_diff}\n"
                    )
            else:
                detail_file.write(
                    "Area of old shape is 0. \n"
                    "Note this should never be in a polygon shapefile.\n"
                )
        else:
            detail_file.write("Cannot compute symmetric difference.\n")
            explain = validation.explain_validity(r_old)
            detail_file.write(f"old: {explain}\n")
            explain = validation.explain_validity(r_new)
            detail_file.write(f"new: {explain}\n")


def compare_poly(
    ax,
    p_old,
    p_new,
    i,
    j=None,
    detail_file=sys.stdout,
    marker_iter=itertools.repeat(None),
    tolerance=0.0,
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
    )

    for k, (r_old, r_new) in enumerate(zip(p_old.interiors, p_new.interiors)):
        compare_rings(
            ax, detail_file, r_old, r_new, next(marker_iter), i, j, k, tolerance
        )
