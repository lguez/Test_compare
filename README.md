This repository contains seven tools:

- `diff_dbf` compares dBase database files (`.dbf` file extension).
- `diff_gv` compares files in Graphviz dot language.
- `diff_shp` compares shapefiles.
- `max_diff_rect` compares CSV files.
- `nccmp` compares NetCDF files.
- `selective_diff` compares directories.
- `test_compare` launches user-defined processes and compares
  results with previous runs.

Each of these tools can be run directly on the command line. Some of
them call others from this repository.

# `selective_diff`

`selective_diff` compares two directories, recursively. The value of
`selective_diff` is that it has better than diff capabilities for
some chosen types of files: NetCDF, numeric CSV, shapefile.

Note that arguments should be two directories, not two files.

Dependencies: see [requirements](requirements.txt), plus ndiff.

# `test_compare`

Test code and compare results.

This program chains runs in directories which do not pre-exist and are
created.

This program reads a JSON test description file. The test description
file must contain a dictionary. The keys of this dictionary should be
the titles of the test. Each title is a string and is used as
directory name. The value for each title is a dictionary describing a
run. Each run is defined by commands, required files (that is, files
required to be present in the current directory at run time),
environment, stdin filename or input, and stdout filename. Each
dictionary must thus include either the key `command` or `commands`,
and may also include the keys:

`main_command`, `description`, `stdout`, `symlink`, `copy`, `env`,
either `stdin_filename` or `input`, `create_file`, `sel_diff_args`

`commands` is a list of commands, `command` is a single command. A
command is a list of strings or a single string. If the command is a
single string then it is split at whitespace. (The command includes
the executable file.)

`main_command` should be an integer value giving the 0-based index of
the main command in the list `commands`. If `main_command` is absent
and `commands` is present then the last command is defined as the main
command. The only difference between the main command and other
commands is that `env`, `stdin_filename` and `input` apply to the main
command only.

The standard output of all the commands is redirected to the file
pointed by `stdout`.

The difference between the keys `stdin_filename` and `input` is that
`input` must be the content of standard input and `stdin_filename`
must be the name of a file that will be redirected to standard
input. `stdin_filename` may be a relative path: it is evaluated after
changing directory to the directory of the test. `stdin_filename` may
be the file created by `create_file`: it is opened after creating the
file. The value of `input` is passed through to the `input` keyword
argument of `subprocess.run`. Usually, the value of `input` should end
with `\n`. If neither `stdin_filename` nor `input` is present, then we
assume that the run does not need any input: no interaction is
allowed.

`create_file` is a list of two elements: the name of the file to
create and its content. The name of the file will normally be a
relative path and the file will be created in the directory of the
test.

If present, `symlink` or `copy` must be a list. Each element of
`symlink` or `copy` must itself be a string or a list of two strings
(no tuple allowed in JSON). If an element of `symlink` or `copy` is a
string then it must be the absolute path to a file or directory that
will be sym-linked or copied to the test directory, with the same
basename. It may contain a shell pattern. If a required element is a
list of two strings then the first string must be the absolute path to
a file or directory that will be sym-linked or copied to the test
directory, with the second string as basename. `symlink` and `copy`
can both be present in a given test description. Generally, files or
directories which will not be modified by the test should be
sym-linked.

If present, `env` must be a dictionary of environment variables and
values. This dictionary will be added to, not replace, the inherited
environment. If an environment variable in `env` was already in the
environment, the value in `env` replaces the old value. This
environment is applied only to the main command.

If `stdout` is not present then the file name for standard output is
constructed from the name of the main command (determined by
`main_command`).

If present, `sel_diff_args` must be a dictionary. The keys must be
arguments of the function `selective_diff`.

The required files and executables must be specified in the JSON input
file with absolute paths. File arguments in commands, if any, also
have to be specified with absolute paths.

This program can also read a JSON file containing string substitutions
to be made in the test description file. This is useful to abbreviate
paths that occur repeatedly in test description file, or to make the
test description file independant of the machine. This abbreviation
file must contain a single dictionary. The strings $PWD and
$tests_old_dir will be automatically substituted in the test
description file, they should not be specified in the file containing
string substitutions.

There may be several JSON test description files on the command
line. If two tests have the same title, the last one will be kept.
