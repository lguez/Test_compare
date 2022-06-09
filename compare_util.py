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
    diff_found = dict(d1) != dict(d2)
    
    if diff_found and not silent:
        if tag: detail_file.write(f"{tag}:\n\n")
        keys_1 = d1.keys()
        keys_2 = d2.keys()
        exclusive_keys = keys_1 ^ keys_2

        for k in exclusive_keys:
            if k in d1:
                detail_file.write(f"{k} in first dictionary only\n")
            else:
                 detail_file.write(f"{k} in second dictionary only\n")

            detail_file.write("-----------\n\n")

        for k in keys_1 & keys_2:
            if d1[k] != d2[k]:
                detail_file.write(f"Different values for key {k}:\n\n")
                detail_file.write(f"{d1[k]}\n\n")
                detail_file.write(f"{d2[k]}\n")
                detail_file.write("-----------\n\n")

    return diff_found

def compare_vars(v1, v2, silent = False, tag = None, detail_file = sys.stdout):
    """v1 and v2 are numpy arrays. Return True if a difference if
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
            detail_file.write("compare_vars: shapes differ\n")
            detail_file.write("-------------\n\n")

        diff_found = True

    return diff_found
