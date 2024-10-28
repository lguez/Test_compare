from os import path

def cat_compar(cat_fname, title_list):
    with open(cat_fname, "w") as f_out:
        for title in title_list:
            fname = path.join(title, "comparison.txt")

            if path.exists(fname):
                with open(fname) as f_in:
                    for line in f_in:
                        f_out.write(line)
