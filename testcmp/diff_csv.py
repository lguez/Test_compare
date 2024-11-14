import sys
import tempfile
import subprocess

from testcmp import diff_txt


def max_diff_rect(path_1, path_2, detail_file, names=None, **other_kwargs):
    """This is a Python wrapper for program max_diff_rect. other_kwargs is
    ignored.

    """

    detail_file.write("\n" + "*" * 10 + "\n\n")

    if names is None:
        detail_file.write(f"max_diff_rect {path_1} {path_2}\n")
    else:
        detail_file.write(f"max_diff_rect {names[0]} {names[1]}\n")

    with tempfile.TemporaryFile("w+") as diff_out:
        subprocess.run(
            ["max_diff_rect", path_1, path_2],
            input="&RECTANGLE FIRST_R=2/\n&RECTANGLE /\nc\nq\n",
            text=True,
            stdout=diff_out,
        )
        diff_out.seek(0)
        detail_file.writelines(diff_out)

    detail_file.write("\n\n")
    return 1


def ndiff(
    path_1,
    path_2,
    detail_file=sys.stdout,
    names=None,
    tolerance=1e-7,
    size_lim=50,
    separators=" ",
):
    """This is a Python wrapper for program ndiff."""

    with tempfile.TemporaryFile("w+") as diff_out:
        cp = subprocess.run(
            [
                "ndiff",
                "-relerr",
                str(tolerance),
                "-separators",
                separators,
                path_1,
                path_2,
            ],
            stdout=diff_out,
            stderr=subprocess.STDOUT,
            text=True,
        )

        if cp.returncode != 0:
            detail_file.write("\n" + "*" * 10 + "\n\n")

            if names is None:
                detail_file.write(f"ndiff {path_1} {path_2}\n")
            else:
                detail_file.write(f"ndiff {names[0]} {names[1]}\n")

            detail_file.write(
                "Comparison with ndiff, tolerance " f"{tolerance}:\n"
            )
            diff_txt.cat_not_too_many(diff_out, size_lim, detail_file)
            detail_file.write("\n")

    return cp.returncode


def numdiff(
    path_1,
    path_2,
    detail_file=sys.stdout,
    names=None,
    tolerance=1e-7,
    size_lim=50,
    separators=" \t",
):
    """This is a Python wrapper for program numdiff."""

    with tempfile.TemporaryFile("w+") as diff_out:
        cp = subprocess.run(
            [
                "numdiff",
                "--quiet",
                "--statistics",
                f"--relative-tolerance={tolerance}",
                "--separators",
                separators + "\n",
                path_1,
                path_2,
            ],
            stdout=diff_out,
            stderr=subprocess.STDOUT,
            text=True,
        )
        # (numdiff says that the separators options must include "\n".)

        if cp.returncode == 1:
            detail_file.write("\n" + "*" * 10 + "\n\n")

            if names is None:
                detail_file.write(f"numdiff {path_1} {path_2}\n")
            else:
                detail_file.write(f"numdiff {names[0]} {names[1]}\n")

            detail_file.write(
                "Comparison with numdiff, tolerance " f"{tolerance}:\n"
            )
            diff_txt.cat_not_too_many(diff_out, size_lim, detail_file)
            detail_file.write("\n")
        elif cp.returncode != 0:
            diff_out.seek(0)
            sys.stdout.writelines(diff_out)
            print("selective_diff: error from numdiff")
            sys.exit(2)

    return cp.returncode
