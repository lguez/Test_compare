import filecmp
from os import path
import pathlib
import pprint
import subprocess
import sys
import tempfile

from wand import image
import jsondiff
import magic

from testcmp import diff_dbf
from testcmp import diff_gv
from testcmp import diff_shp
from testcmp import nccmp
from testcmp import diff_txt
from testcmp import diff_csv


def diff_png(path_1, path_2, detail_file):
    with image.Image(filename=path_1) as image1, image.Image(
        filename=path_2
    ) as image2:
        if image1.signature == image2.signature:
            # The difference must be only in metadata
            n_diff = 0
        else:
            detail_file.write("\n" + "*" * 10 + "\n\n")
            detail_file.write(f"diff_png {path_1} {path_2}\n")
            diff_img, distorsion = image2.compare(image1, metric="absolute")
            detail_file.write(f"Number of different pixels: {distorsion}\n")
            filename = path.join(path.dirname(path_2), "diff_image.png")
            diff_img.save(filename=filename)
            detail_file.write(f"See {filename}\n\n")
            n_diff = 1

    return n_diff


def diff_json(path_1, path_2, detail_file):
    with open(path_1) as f_obj_1, open(path_2) as f_obj_2:
        my_diff = jsondiff.diff(f_obj_1, f_obj_2, load=True, syntax="symmetric")

    if my_diff:
        detail_file.write("\n" + "*" * 10 + "\n\n")
        detail_file.write(f"diff_json {path_1} {path_2}\n")
        pprint.pp(my_diff, stream=detail_file)
        n_diff = 1
    else:
        n_diff = 0

    return n_diff


def max_diff_nc(path_1, path_2, detail_file):
    """This is a Python wrapper for program max_diff_nc.sh."""

    detail_file.write("\n" + "*" * 10 + "\n\n")
    detail_file.write(f"max_diff_nc {path_1} {path_2}\n")

    with tempfile.TemporaryFile("w+") as diff_out:
        subprocess.run(
            ["max_diff_nc.sh", path_1, path_2], text=True, stdout=diff_out
        )
        diff_out.seek(0)
        detail_file.writelines(diff_out)

    return 1


def nccmp_Ziemlinski(path_1, path_2, detail_file):
    with tempfile.TemporaryFile("w+") as diff_out:
        cp = subprocess.run(
            ["nccmp", "--data", "--history", "--force", path_1, path_2],
            text=True,
            stdout=diff_out,
            stderr=subprocess.STDOUT,
        )

        if cp.returncode != 0:
            detail_file.write("\n" + "*" * 10 + "\n\n")
            detail_file.write(f"nccmp_Ziemlinski {path_1} {path_2}\n")
            detail_file.write("Comparison with nccmp by Ziemlinski:\n")
            diff_out.seek(0)
            detail_file.writelines(diff_out)

    return cp.returncode


def diff_nc_ncdump(path_1, path_2, detail_file, size_lim):
    f1_ncdump = tempfile.NamedTemporaryFile("w+")
    f2_ncdump = tempfile.NamedTemporaryFile("w+")
    subprocess.run(["ncdump", "-h", path_1], stdout=f1_ncdump)
    subprocess.run(["ncdump", "-h", path_2], stdout=f2_ncdump)

    if filecmp.cmp(f1_ncdump.name, f2_ncdump.name, shallow=False):
        n_diff = 0
    else:
        detail_file.write(
            f"ncdumps of headers of {path_1} and {path_2} " "are different\n"
        )
        n_diff = diff_txt.diff_txt(
            f1_ncdump.name, f2_ncdump.name, size_lim, detail_file
        )

    f1_ncdump.close()
    f2_ncdump.close()
    n_diff += nccmp.nccmp(
        path_1, path_2, data_only=True, detail_file=detail_file
    )
    return min(n_diff, 1)


class DetailedDiff:
    def __init__(
        self,
        size_lim=50,
        diff_dbf_pyshp=False,
        diff_csv_option="",
        diff_nc="",
        tolerance=1e-7,
        ign_att=None,
    ):
        self.size_lim = size_lim
        self.tolerance = tolerance
        self.diff_nc = diff_nc
        self.ign_att = ign_att

        if diff_dbf_pyshp:
            self._diff_dbf = diff_dbf.diff_dbf
        else:
            self._diff_dbf = self._diff_dbf_dbfdump

        if diff_csv_option == "numdiff":
            self._diff_csv = diff_csv.numdiff
        elif diff_csv_option == "max_diff_rect":
            self._diff_csv = diff_csv.max_diff_rect
        else:
            self._diff_csv = diff_csv.ndiff

    def diff(self, path_1, path_2, detail_file=sys.stdout):
        suffix = pathlib.PurePath(path_1).suffix
        file_type = magic.from_file(path.realpath(path_1))

        if suffix == ".dbf":
            n_diff = self._diff_dbf(path_1, path_2, detail_file)
        elif suffix == ".csv":
            n_diff = self._diff_csv(
                path_1,
                path_2,
                detail_file,
                tolerance=self.tolerance,
                size_lim=self.size_lim,
            )
        elif suffix == ".nc":
            if self.diff_nc == "ncdump":
                n_diff = diff_nc_ncdump(
                    path_1, path_2, detail_file, self.size_lim
                )
            elif self.diff_nc == "max_diff_nc":
                n_diff = max_diff_nc(path_1, path_2, detail_file=detail_file)
            elif self.diff_nc == "Ziemlinski":
                n_diff = nccmp_Ziemlinski(
                    path_1, path_2, detail_file=detail_file
                )
            else:
                n_diff = nccmp.nccmp(
                    path_1,
                    path_2,
                    detail_file=detail_file,
                    ign_att=self.ign_att,
                )
        elif suffix == ".shp":
            n_diff = diff_shp.diff_shp(
                path_1,
                path_2,
                detail_file=detail_file,
                tolerance=self.tolerance,
                max_n_diff=self.size_lim // 5,
            )
        elif suffix == ".png":
            n_diff = diff_png(path_1, path_2, detail_file)
        elif suffix == ".gv":
            n_diff = diff_gv.diff_gv(path_1, path_2, detail_file)
        elif suffix == ".json":
            n_diff = diff_json(path_1, path_2, detail_file)
        elif suffix == ".txt" or "text" in file_type:
            n_diff = diff_txt.diff_txt(
                path_1, path_2, self.size_lim, detail_file
            )
        elif file_type == "empty":
            detail_file.write("\n" + "*" * 10 + "\n\n")
            detail_file.write(f"diff {path_1} {path_2}\n")
            detail_file.write("Old file is empty\n\n")
            n_diff = 1
        else:
            detail_file.write("\n" + "*" * 10 + "\n\n")
            detail_file.write(f"diff {path_1} {path_2}\n")
            detail_file.write("Detailed diff not implemented\n\n")
            n_diff = 1

        return n_diff

    def _diff_dbf_dbfdump(self, path_1, path_2, detail_file):
        f1_dbfdump = tempfile.NamedTemporaryFile("w+")
        f2_dbfdump = tempfile.NamedTemporaryFile("w+")
        subprocess.run(["dbfdump", path_1], stdout=f1_dbfdump)
        subprocess.run(["dbfdump", path_2], stdout=f2_dbfdump)

        if filecmp.cmp(f1_dbfdump.name, f2_dbfdump.name, shallow=False):
            n_diff = 0
        else:
            n_diff = self._diff_csv(
                f1_dbfdump.name,
                f2_dbfdump.name,
                detail_file,
                names=(path_1, path_2),
            )

        f1_dbfdump.close()
        f2_dbfdump.close()
        return n_diff
