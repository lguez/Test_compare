import sys
import io

import numpy as np
from numpy import ma

def cmp(v1, v2, silent = False, tag = None, detail_file = sys.stdout):
    if isinstance(v1, set) and isinstance(v2, set):
        diff_found = diff_set(v1, v2, silent, tag, detail_file)
    else:
        diff_found = v1 != v2

        if diff_found and not silent:
            if tag: detail_file.write(f"{tag}:\n\n")
            detail_file.write(f"{v1}\n\n")
            detail_file.write(f"{v2}\n")
            detail_file.write("-------------\n\n")

    return diff_found

def diff_dict(d1, d2, silent = False, tag = None, detail_file = sys.stdout):
    if silent:
        diff_found = d1.keys() != d2.keys()

        if not diff_found:
            # {d1.keys() == d2.keys()}
            for k in d1:
                if np.any(d1[k] != d2[k]):
                    diff_found = True
                    break
    else:
        # We need to insert a header before detailed diagnostic, but only
        # if we find differences, so create a new text stream:
        detail_subfile = io.StringIO()

        if tag: detail_subfile.write(f"{tag}:\n\n")
        keys_1 = d1.keys()
        keys_2 = d2.keys()
        diff_found = False
        diff_keys = keys_1 - keys_2

        if len(diff_keys) != 0:
            diff_found = True
            detail_subfile.write(f"{diff_keys} in first dictionary only\n\n")

        diff_keys = keys_2 - keys_1

        if len(diff_keys) != 0:
            diff_found = True
            detail_subfile.write(f"{diff_keys} in second dictionary only\n\n")

        detail_subfile.write("-----------\n\n")

        for k in keys_1 & keys_2:
            if np.any(d1[k] != d2[k]):
                diff_found = True
                detail_subfile.write(f"Different values for key {k}:\n\n")
                detail_subfile.write(f"{d1[k]}\n\n")
                detail_subfile.write(f"{d2[k]}\n")
                detail_subfile.write("-----------\n\n")

        if diff_found:
            detail_diag = detail_subfile.getvalue()
            detail_file.write(detail_diag)

        detail_subfile.close()

    return diff_found

def diff_set(v1, v2, silent = False, tag = None, detail_file = sys.stdout):
    diff_found = v1 != v2

    if diff_found and not silent:
        if tag: detail_file.write(f"{tag}:\n\n")

        for k in v1 ^ v2:
            if k in v1:
                detail_file.write(f"{k} in first set only\n")
            else:
                detail_file.write(f"{k} in second set only\n")

            detail_file.write("-----------\n\n")

    return diff_found

def cmp_ndarr(v1, v2, silent = False, tag = None, detail_file = sys.stdout):
    """v1 and v2 are numpy arrays. Return True if a difference is
    found."""
    
    if v1.shape == v2.shape:
        if v1.size == 0:
            diff_found = False
        else:
            mask1 = ma.getmaskarray(v1[:])
            mask2 = ma.getmaskarray(v2[:])
            diff_found = np.any(mask1 != mask2)

            if not diff_found:
                try:
                    compressed1 = v1[:].compressed()
                    compressed2 = v2[:].compressed()
                except AttributeError:
                    compressed1 = v1[:]
                    compressed2 = v2[:]

                diff_found = np.any(compressed1 != compressed2)

            if diff_found and not silent:
                if tag: detail_file.write(f"{tag}:\n")
                detail_file.write("Different content\n")
                detail_file.write("-------------\n\n")
    else:
        if not silent:
            if tag: detail_file.write(f"{tag}:\n")
            detail_file.write("cmp_ndarr: shapes differ\n")
            detail_file.write("-------------\n\n")

        diff_found = True

    return diff_found
