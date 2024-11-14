import difflib
import tempfile


def cat_not_too_many(file_in, size_lim, file_out):
    """file_in and file_out should be existing file objects."""

    count = 0
    file_in.seek(0)

    while True:
        line = file_in.readline()
        count += 1
        if line == "" or count > size_lim:
            break

    if count <= size_lim:
        file_in.seek(0)
        file_out.writelines(file_in)
    else:
        file_out.write("Too many lines in diff output\n")


def diff_txt(path_1, path_2, size_lim, detail_file):
    """Process path_1 and path_2 as text files."""

    detail_file.write("\n" + "*" * 10 + "\n\n")
    detail_file.write(f"diff_txt {path_1} {path_2}\n")

    with open(path_1) as f:
        fromlines = f.readlines()

    with open(path_2) as f:
        tolines = f.readlines()

    my_diff = difflib.unified_diff(
        fromlines, tolines, fromfile=path_1, tofile=path_2, n=0
    )

    with tempfile.TemporaryFile("w+") as diff_out:
        diff_out.writelines(my_diff)
        cat_not_too_many(diff_out, size_lim, detail_file)

    detail_file.write("\n")
    return 1
