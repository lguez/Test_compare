def cmp(v1, v2, silent = False, tag = None):
    diff_found = v1 != v2
    
    if diff_found and not silent:
        if tag: print(tag, ":\n")
        print(v1)
        print()
        print(v2)
        print("-------------\n")

    return diff_found
