#!/usr/bin/env python3

from testcmp import detailed_diff
from testcmp import diff_csv

diff_csv.ndiff(
    "Test_dir1/parallel_compilation.csv", "Test_dir2/parallel_compilation.csv"
)
diff_csv.ndiff(
    "Test_dir1/parallel_compilation.csv",
    "Test_dir2/parallel_compilation.csv",
    separators=",",
)
diff_csv.numdiff(
    "Test_dir1/parallel_compilation.csv",
    "Test_dir2/parallel_compilation.csv",
    separators=",",
)
dd = detailed_diff.DetailedDiff()
dd.diff(
    "Test_dir1/parallel_compilation.csv", "Test_dir2/parallel_compilation.csv"
)
dd.diff("Test_dir1/feuilles.txt", "Test_dir2/feuilles.txt")
dd = detailed_diff.DetailedDiff(diff_csv_option="numdiff")
dd.diff(
    "Test_dir1/parallel_compilation.csv", "Test_dir2/parallel_compilation.csv"
)
dd = detailed_diff.DetailedDiff(diff_csv_option="max_diff_rect")
dd.diff(
    "Test_dir1/parallel_compilation.csv", "Test_dir2/parallel_compilation.csv"
)
