This repository contains seven tools:

- `diff_dbf.py` compares dBase database files (`.dbf` file extension).
- `diff_gv.py` compares files in Graphviz dot language.
- `diff_shp.py` compares shapefiles.
- `max_diff_rect` compares CSV files.
- `nccmp.py` compares NetCDF files.
- `selective_diff.py` compares directories.
- `test_compare.py` launches user-defined processes and compares
  results with previous runs.

Each of these tools can be run directly on the command line. Some of
them call others from this repository.

# `selective_diff`

`selective_diff` compares two directories, recursively. The value of
`selective_diff` is that it has better than diff capabilities for
some chosen types of files: NetCDF, numeric CSV, shapefile.

Note that arguments should be two directories, not two files.

Dependencies: [python3-wand](https://github.com/emcconville/wand),
[networkx](https://networkx.org),
[python-magic](https://github.com/ahupp/python-magic), ndiff,
matplotlib, netCDF4, yachalk.

# `test_compare`

Test code and compare results.
