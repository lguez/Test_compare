#!/usr/bin/env python3

from networkx import nx_agraph

def diff_gv(path_1, path_2, detail_file):
    """For Graphviz files."""

    G1 = nx_agraph.read_dot(path_1)
    G2 = nx_agraph.read_dot(path_2)

    if G1 == G2:
        returncode = 0
    else:
        returncode = 1
        detail_file.write('\n' + "*" * 10 + '\n\n')
        detail_file.write(f"diff {path_1} {path_2}\n")
        detail_file.write(f"Equality of nodes: {G1.nodes == G2.nodes}\n")
        detail_file.write(f"Equality of adjacencies: {G1.adj == G2.adj}\n")
        detail_file.write(f"Equality of attributes: {G1.graph == G2.graph}\n")

    return returncode

if __name__ == "__main__":
    import sys
    
    returncode = diff_gv(sys.argv[1], sys.argv[2], sys.stdout)
    sys.exit(returncode)
