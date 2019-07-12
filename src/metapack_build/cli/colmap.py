# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
Metapack CLI program for creating new metapack package directories
"""

import argparse
import csv
import sys
from pathlib import Path

from metapack import Downloader
from metapack.cli.core import MetapackCliMemo as _MetapackCliMemo
from metapack.cli.core import err, list_rr, prt
from metapack_build.core import alt_col_name

downloader = Downloader.get_instance()


class MetapackCliMemo(_MetapackCliMemo):

    def __init__(self, args, downloader):
        super().__init__(args, downloader)


def colmap_args(subparsers):
    """
    Create and manipulate column maps for datasets split across multiple files.

    """
    parser = subparsers.add_parser(
        'colmap',
        help='Create and manipulate column maps for datasets split across multiple files.',
        description=colmap_args.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    cmdsp = parser.add_subparsers(help='sub-command help')

    cmdp = cmdsp.add_parser('new', help='Create a new column map for a group of columns')
    cmdp.set_defaults(run_command=run_colmap_new)

    cmdp.add_argument('-f', '--force', action='store_true', help='Force overwritting existing file')

    cmdp.add_argument('-p', '--print', action='store_true', help='Print the colmap instead of writing to a file')

    cmdp.add_argument('colmap_name', help='Colmap name, set in a ColMap argument child on a resource or reference')

    cmdp.add_argument('metatabfile', nargs='?',
                      help="Path or URL to a metatab file. If not provided, defaults to 'metadata.csv' ")

    cmdp = cmdsp.add_parser('test', help='check the colmap for a resource')
    cmdp.set_defaults(run_command=run_colmap_test)

    cmdp.add_argument('metatabfile', nargs='?',
                      help="Path or URL to a metatab file. If not provided, defaults to 'metadata.csv' ")

    return parser


def get_resources(m):
    from itertools import chain

    resources = []

    for r in chain(m.doc.references(), m.doc.resources()):
        if r.get_value('colmap') == m.args.colmap_name:
            resources.append(r)

    return resources


def run_colmap_new(args):
    m = MetapackCliMemo(args, downloader)

    resources = get_resources(m)

    if not resources:
        err(f"No resources found with colmap name '{m.args.colmap_name}'")

    # Collect all of the headers, into a list of headers,
    # and the union of all of them in col_index
    col_index = []
    headers = []

    for r in resources:
        h = r.headers

        col_index += [alt_col_name(c) for c in h if alt_col_name(c) not in col_index]
        headers.append(h)

    # Create lists, of the same length as the index, of the source
    # column names, at the same position as the alt_col_name is in the col_index
    data = [col_index]

    for header in headers:
        new_row = [None] * len(col_index)
        for c in header:
            new_row[col_index.index(alt_col_name(c))] = c

        data.append(new_row)

    t = [['index'] + [r.name for r in resources]] + list(zip(*data))  # zip transposes rows into columns.

    path = Path(f"colmap-{m.args.colmap_name}.csv")

    if m.args.print:
        from tabulate import tabulate
        prt(tabulate(t[1:], headers=t[0]))
    else:
        if path.exists() and not m.args.force:
            err(f"Col map file '{str(path)}' already exists. Use -f to overwrite")

        else:
            with path.open('w') as f:
                csv.writer(f).writerows(t)
            prt(f"Wrote {str(path)}")


def get_col_map(r):
    return r.header_map

    cm_name = r.get_value('colmap')

    if not cm_name:
        err(f"Resource '{r.name}' does not have a ColMap property")

    path = Path(f"colmap-{cm_name}.csv")

    if not path.exists():
        err(f"Colmap file '{str(path)}' does nto exist")

    with path.open() as f:
        cm = {}
        for row in csv.DictReader(f):
            if row[r.name]:
                cm[row[r.name]] = row['index']

    return cm


def run_colmap_test(args):
    m = MetapackCliMemo(args, downloader)

    r = m.get_resource()

    if not r:
        prt('Select a resource to run:')
        list_rr(m.doc)
        sys.exit(0)

    cm = get_col_map(r)

    print(cm)
