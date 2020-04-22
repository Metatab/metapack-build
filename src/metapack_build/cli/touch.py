# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
Show path to include.mk for building packages with makefiles.
"""

import argparse
import sys
from pathlib import Path

import yaml

from metapack import MetapackDoc, open_package
from metapack.cli.core import MetapackCliMemo, prt
from metapack.package import Downloader

from .build import last_build_marker_path, trial_build_marker_path

downloader = Downloader.get_instance()


def touch_args(subparsers):
    """
    The make command will build a package with a trial build, setting the Version.Build
    value to trial. If the hashes on the data for the trial build are
    different from the most recent build, the package is marked for rebuilding
    by a following call to `mp build`.

    The package is marked for rebuilding by touching ( updated times )
    on the metadata file, or by incrementing the version.

    This only works if the version number of the package is a semantic version,
    and there was a prior build in the _packages directory

    """
    parser = subparsers.add_parser(
        'touch',
        help='Mark a package for updating if the data has changed',
        description=touch_args.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('metatabfile', nargs='?',
                        help="Path or URL to a metatab file. If not provided, defaults to 'metadata.csv'. "
                        )

    parser.add_argument('-r', '--result', action='store_true', default=False,
                        help="If mp -q flag set, still report results")

    parser.add_argument('-b', '--build', action='store_true', default=False,
                        help="Build a trial version of the package")

    parser.add_argument('-I', '--increment', action='store_true', default=False,
                        help="With -b, increment the version number before building")

    parser.add_argument('-W', '--write-hashes', action='store_true', default=False,
                        help="Record the hashes of the data in the last built package.")

    parser.add_argument('-R', '--read-hashes', action='store_true', default=False,
                        help="Display the hashes of the last buildt and trial package")

    parser.add_argument('-C', '--compare', action='store_true', default=False,
                        help="Compare hashes of last built package to stored hashes, return non-zero status code if different")

    parser.add_argument('-T', '--trial', action='store_true', default=False,
                        help="With -h, record hashes of the last trial package.")

    parser.set_defaults(run_command=touch_cmd)


def touch_cmd(args):
    # Always turn the cache off; won't update otherwise
    downloader.use_cache = False
    args.no_cache = True

    m = MetapackCliMemo(args, downloader)

    if m.args.build:
        build(m)

    if args.compare:
        compare_hashes(m)  # This will exit, so nothing else after will run

    if args.write_hashes:
        write_hashes(m)

    if args.read_hashes:
        read_hashes(m)


def build(m):

    raise NotImplementedError()

    def mp(*args):
        pass

    name = m.doc.name

    lb_file = m.package_root.fspath.joinpath('.last_build')

    if m.args.result:
        prt = print
    else:
        from metapack.cli.core import prt

    if lb_file.exists():
        # Run a test build
        ft_args = ['build', '-FT']
        if m.args.no_cache:
            ft_args = ['-n'] + ft_args
        mp(ft_args, do_cli_init=False)

        tb_path = m.package_root.fspath.joinpath('.trial_build').read_text()
        lb_path = lb_file.read_text()

        tdoc = MetapackDoc(tb_path)
        ldoc = MetapackDoc(lb_path)

        diff_hashes = 0

        for t_r in tdoc.resources():
            l_r = ldoc.resource(t_r.name)

            h1 = t_r.raw_row_generator.hash
            h2 = l_r.raw_row_generator.hash

            if h1 != h2:
                diff_hashes += 1

        if diff_hashes == 0:
            prt(f'👍 {name}: Hashes Unchanged: will not rebuild')
            return

        prt(f'🛠 {name}: Hashes changed. Marked for rebuilding')
        Path(m.mt_file.fspath).touch()

        if m.args.increment:
            m.doc.update_name(mod_version='+')
            m.doc.write()
    else:
        prt(f'🛠 {name}: No previous build')


def reclaim_trial(m):
    tm = trial_build_marker_path(m).read_text()
    print(tm)

    p = open_package(tm)

    print(p.package_url)
    print(m.doc.package_url)

    print(p['Root'].get_value('Version.Build'))

    vt = p['Root'].find_first('Version')

    evt = m.doc['Root'].find_first('Version')

    m.doc['Root'].remove_term(evt)
    m.doc['Root'].add_term(vt)

    m.doc.write()


def write_hashes(m):
    pm = last_build_marker_path(m)

    hashes = {}

    if pm.exists():
        hashes['last_package'] = pm.read_text()

        p = open_package(hashes['last_package'])

        hashes['last_hashes'] = {r.name: r.raw_row_generator.hash for r in p.resources()}

    tm = trial_build_marker_path(m)

    if tm.exists():
        hashes['trial_package'] = tm.read_text()

        p = open_package(hashes['trial_package'])

        hashes['trial_hashes'] = {r.name: r.raw_row_generator.hash for r in p.resources()}

    hp = Path(m.package_root.fspath, '.hashes.yaml')

    hp.write_text(yaml.safe_dump(hashes))


def read_hashes(m):
    hp = Path(m.package_root.fspath, '.hashes.yaml')

    if not hp.exists():
        return

    print(hp.read_text())


def compare_hashes(m):
    hp = Path(m.package_root.fspath, '.hashes.yaml')

    if not hp.exists():
        print("!!! NO HASHES: ", hp)
        return

    hashes = yaml.safe_load(hp.read_text())

    pm = last_build_marker_path(m)

    diffs = 0
    if pm.exists():

        p = open_package(pm.read_text())

        for r in p.resources():
            h1 = r.raw_row_generator.hash
            h2 = hashes['last_hashes'].get(r.name)

            if h1 != h2:
                diffs += 1

    prt(f"{diffs} diffs")

    if diffs:
        sys.exit(1)
    else:
        sys.exit(0)
