# Copyright (c) 2020 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
Task definitions for managing packages, used with invoke
"""

from pathlib import Path

from invoke import Collection, task

from metapack.cli.core import get_config


@task(default=True, optional=['force'])
def build(c, force=None):
    """Build a filesystem package."""

    force_flag = '-F' if force else ''

    c.run(f"mp build -r {force_flag}", pty=True)


@task
def publish(c, s3_bucket=None, wp_site=None, groups=[], tags=[]):
    " Publish to s3 and wordpress, if the proper bucket and site variables are defined"

    wp_site = c.metapack.wp_site or wp_site
    s3_bucket = c.metapack.s3_bucket or s3_bucket

    groups = c.metapack.groups or groups
    tags = c.metapack.tags or tags

    group_flags = ' '.join([f"-g{g}" for g in groups])
    tag_flags = ' '.join([f"-t{t}" for t in tags])

    if s3_bucket:
        c.run(f"mp s3 -s {s3_bucket}", pty=True)
    if wp_site:
        c.run(f"mp wp -s {wp_site} {group_flags} {tag_flags} -p", pty=True)

    if not s3_bucket and not wp_site:
        print("Neither s3 bucket nor wp site config specified; nothing to do")


@task(optional=['force'])
def make(c, force=None, s3_bucket=None, wp_site=None, groups=[], tags=[]):
    """Build, write to S3, and publish to wordpress, but only if necessary"""

    groups = c.metapack.groups or groups
    tags = c.metapack.tags or tags

    wp_site = c.metapack.wp_site or wp_site
    s3_bucket = c.metapack.s3_bucket or s3_bucket

    force_flag = '-F' if force else ''

    group_flags = ' '.join([f"-g{g}" for g in groups])
    tag_flags = ' '.join([f"-t{t}" for t in tags])

    wp_flags = f' -w {wp_site} {group_flags} {tag_flags}' if wp_site else ''
    s3_flags = f' -s {s3_bucket}' if s3_bucket else ''

    c.run(f'mp --exceptions -q  make {force_flag}  -r  -b {s3_flags} {wp_flags}', pty=True)


@task
def clean(c):
    c.run('rm -rf _packages')


@task
def pip(c):
    """Install any python packages specified in a requirements.txt file"""

    if Path('requirements.txt').exists():
        c.run('pip install -q -r requirements.txt')


@task
def config(c):
    """Print invoke's configuration"""
    from textwrap import dedent
    from os import getcwd

    print(dedent(f"""
    Dir:            {getcwd()}
    Groups:         {c.metapack.groups}
    Tags:           {c.metapack.tags}
    Wordpress Site: {c.metapack.wp_site}
    S3 Bucket:      {c.metapack.s3_bucket}
    """))


ns = Collection(build, publish, make, config, clean, pip)

metapack_config = get_config().get('invoke', {})

ns.configure(
    {
        'metapack':
            {
                's3_bucket': metapack_config.get('s3_bucket'),
                'wp_site': metapack_config.get('wp_site'),
                'groups': None,
                'tags': None
            }
    }
)
