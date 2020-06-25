# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
Show path to include.mk for building packages with makefiles.
"""

import argparse
from datetime import datetime, timedelta

from dateutil.parser import parse

from metapack.cli.core import MetapackCliMemo, warn
from metapack.cli.mp import base_parser
from metapack.package import Downloader
from metapack.util import iso8601_duration_as_seconds
from metapack_build.cli.build import _build_cmd
from metapack_build.cli.s3 import run_s3
from metapack_build.cli.touch import write_hashes


def make_args(subparsers):
    """
    The make command will:

        * Force building a package, with the downloader cache off ( it will always fetch and build )
        * Optionally upload package to S3
        * Optionally publishes uploaded package to Wordpress

    However, if an UpdateFrequency value is set ( an ISO8601 time duration )
    the update will not run until a time after Root.Modified + Root.UpdateFrequency
    unless the --force option used.

    """
    parser = subparsers.add_parser(
        'make',
        help='Mark a package for updating if the data has changed',
        description=make_args.__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('metatabfile', nargs='?',
                        help="Path or URL to a metatab file. If not provided, defaults to 'metadata.csv'. "
                        )

    parser.add_argument('-b', '--build', action='store_true', default=False,
                        help='Build the package')

    parser.add_argument('-z', '--zip', action='store_true', default=False,
                        help='With -b, also build a Zip file package')

    parser.add_argument('-s', '--s3', help="URL to S3 where packages will be stored", required=False)

    parser.add_argument('-w', '--wordpress-site', help="Wordpress site name, in the .metapack.yaml configuration file",
                        required=False)

    parser.add_argument('-g', '--group', nargs='?', action='append', help="Assign an additional group. Can be used "
                                                                          "multiple times, one onece with values "
                                                                          "separated by commas")

    parser.add_argument('-t', '--tag', nargs='?', action='append', help="Assign an additional tag. Can be used "
                                                                        "multiple times, or once with values "
                                                                        "separated by commas")

    parser.add_argument('-r', '--result', action='store_true', default=False,
                        help="If mp -q flag set, still report results")

    parser.add_argument('-F', '--force', action='store_true', default=False,
                        help="Force the build")

    parser.add_argument('-n', '--dry-run', action='store_true', default=False,
                        help="Don't make, just report if package would be built")

    parser.add_argument('-I', '--increment', action='store_true', default=False,
                        help="With -b, increment the version number before building")

    parser.add_argument('-p', '--profile', help="Name of a BOTO or AWS credentials profile", required=False)

    parser.set_defaults(run_command=make_cmd)


def mk_ns(args, cmd, *largs):
    parser = base_parser()

    new_args = [cmd]

    if args.result:
        new_args += ['-r']

    new_args += list(largs)

    return parser.parse_args(new_args)


def next_update_time(m):
    """Return the next update time. If the UpdateFrequency or Modified
    """

    last_mod = m.doc['Root'].find_first_value('Root.Modified')

    if last_mod:
        last_mod = parse(last_mod)
    else:
        return False

    uf = m.doc['Root'].find_first_value('Root.UpdateFrequency')

    if uf:
        uf = timedelta(seconds=iso8601_duration_as_seconds(uf))
    else:
        return False

    return (last_mod + uf).date()


def should_build(m):
    force = m.args.force

    p = m.filesystem_package

    now = datetime.now().date()

    update_time = next_update_time(m)

    if m.doc['Root'].find_first_value('Root.UpdateFrequency'):
        has_uf = True
    else:
        has_uf = False


    if force:
        reason = 'Forcing build'
        should_build = True
    elif p.is_older_than_metadata():
        reason = 'Metadata is younger than package'
        should_build = True
    elif not p.exists():
        reason = "Package doesn't exist"
        should_build = True
    elif update_time is not False and update_time <= now:
        reason = 'Last build past update frequency'
        should_build = True
    else:
        if has_uf and update_time is not False:
            reason = f'UpdateFrequency specifies next build at {update_time}'
        else:
            reason = 'Package source has not changed since last build'

        should_build = False

    return should_build, reason


def make_cmd(args):
    # Always turn the cache off; builds won't update otherwise

    downloader = Downloader.get_instance()

    m = MetapackCliMemo(args, downloader)

    sb, reason = should_build(m)

    print(f"🛠  {m.doc.name}")

    if not sb:
        print(f"☑️  Not building; {reason}")
        return
    else:
        print(f"⚙️  Building: {reason}")

    if args.dry_run:
        return

    if not any([args.build, args.s3, args.wordpress_site]):
        args.build = True

    if args.build:
        downloader = Downloader.get_instance()
        downloader.use_cache = False

        ns = mk_ns(args, 'build', '-X', '-F', '-f', '-z' if args.zip else '')

        do_uploads = build_is_different = _build_cmd(ns)

        downloader.reset_callback()

    else:
        build_is_different = False
        do_uploads = True

    if do_uploads and args.s3:
        ns = mk_ns(args, 's3')
        ns.s3 = args.s3
        if args.profile:
            ns.profile = args.profile
        ns.metatabfile = args.metatabfile

        run_s3(ns)

    if do_uploads and args.wordpress_site:

        try:
            from metapack_wp.wp import run_wp
            ns = mk_ns(args, 'wp')
            ns.site_name = args.wordpress_site
            ns.source = args.metatabfile
            ns.group = args.group
            ns.tag = args.tag

            run_wp(ns)
        except ModuleNotFoundError:
            warn("Can't publish to Wordpress: {str(e)}")

    m = MetapackCliMemo(args, downloader)

    # If the build changed, update the version for the next build
    if build_is_different:
        # Increment the version number

        m.doc.update_name(mod_version='+')

        print(f"➕ incremented version to  {m.doc.name}")

        write_hashes(m)

        m.doc.write()  # Updates modified time
