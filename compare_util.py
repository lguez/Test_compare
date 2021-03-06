import numpy as np

def cmp(v1, v2, silent = False, tag = None):
    diff_found = v1 != v2
    
    if diff_found and not silent:
        if tag: print(tag, ":\n")
        print(v1)
        print()
        print(v2)
        print("-------------\n")

    return diff_found

def diff_dict(d1, d2, silent = False, tag = None):
    diff_found = dict(d1) != dict(d2)
    
    if diff_found and not silent:
        if tag: print(tag, ":\n")
        keys_1 = d1.keys()
        keys_2 = d2.keys()
        exclusive_keys = keys_1 ^ keys_2

        for k in exclusive_keys:
            if k in d1:
                print(k, "in first dictionary only")
            else:
                 print(k, "in second dictionary only")

            print("-----------\n")

        for k in keys_1 & keys_2:
            if d1[k] != d2[k]:
                print("Different values for key", k, ":")
                print()
                print(d1[k])
                print()
                print(d2[k])
                print("-----------\n")

    return diff_found

def compare_vars(v1, v2, silent = False, tag = None):
    """v1 and v2 are numpy arrays. Return True if a difference if
    found."""
    
    if v1.shape == v2.shape:
        if v1.size == 0:
            if not silent:
                if tag: print(tag, ":")
                print('Zero-sized array')
                print("-------------\n")
                
            diff_found = False
        else:
            if np.all(v1[:] == v2[:]):
                diff_found = False
            else:
                if not silent:
                    if tag: print(tag, ":")
                    print("Different content")
                    print("-------------\n")
                    
                diff_found = True
    else:
        if not silent:
            if tag: print(tag, ":")
            print("compare_vars: shapes differ")
            print("-------------\n")

        diff_found = True

    return diff_found
