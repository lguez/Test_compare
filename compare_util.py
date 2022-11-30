import numpy as np
from numpy import ma
import sys

def cmp(v1, v2, silent = False, tag = None, detail_file = sys.stdout):
    diff_found = v1 != v2
    
    if diff_found and not silent:
        if tag: detail_file.write(f"{tag}:\n\n")
        detail_file.write(f"{v1}\n\n")
        detail_file.write(f"{v2}\n")
        detail_file.write("-------------\n\n")

    return diff_found

def diff_dict(d1, d2, silent = False, tag = None, detail_file = sys.stdout):
    try:
        diff_found = d1 != d2
    except ValueError:
        # This happens if values are numpy arrays with more than one
        # element. Let us just move past that for now.
        diff_found = True
    
    if diff_found and not silent:
        if tag: detail_file.write(f"{tag}:\n\n")
        keys_1 = d1.keys()
        keys_2 = d2.keys()

        for k in keys_1 ^ keys_2:
            if k in d1:
                detail_file.write(f"{k} in first dictionary only\n")
            else:
                detail_file.write(f"{k} in second dictionary only\n")

            detail_file.write("-----------\n\n")

        for k in keys_1 & keys_2:
            if np.any(d1[k] != d2[k]):
                detail_file.write(f"Different values for key {k}:\n\n")
                detail_file.write(f"{d1[k]}\n\n")
                detail_file.write(f"{d2[k]}\n")
                detail_file.write("-----------\n\n")

    return diff_found

def cmp_ndarr(v1, v2, silent = False, tag = None, detail_file = sys.stdout):
    """v1 and v2 are numpy arrays. Return True if a difference is
    found."""
    
    if v1.shape == v2.shape:
        if v1.size == 0:
            if not silent:
                if tag: detail_file.write(f"{tag}:\n")
                detail_file.write('Zero-sized array\n')
                detail_file.write("-------------\n\n")
                
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
