# Copyright (c) 2020 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
Task definitions for managing packages, used with invoke
"""

from pathlib import Path

from invoke import Collection, task

from metapack import open_package
from metapack.cli.core import get_config
from rowgenerators import parse_app_url


@task(default=True, optional=['force'])
def build(c, force=None):
    """Build a filesystem package."""

    force_flag = '-F' if force else ''

    c.run(f"mp  build -r {force_flag}", pty=True)


@task
def s3(c, s3_bucket=None):
    """ Publish to s3, if the proper bucket and site variables are defined

    If the package should not be published, add a 'Redistribution'  Term to the root level
    of the metadata. It can take two values:

        "hidden": publish to S3, but not wordpress
        "private": Don't publish to either S3 or Wordpress

    """

    s3_bucket = c.metapack.s3_bucket or s3_bucket

    pkg = open_package('./metadata.csv')

    redist = pkg.find_first_value('Root.Redistribution')
    name = pkg.name

    if redist == 'private':
        print(f"⚠️  Package {name} is private; won't upload to s3")
    elif s3_bucket:
        c.run(f"mp s3 -s {s3_bucket}", pty=True)


@task
def publish(c, s3_bucket=None, wp_site=None, groups=[], tags=[]):
    """ Publish to s3 and wordpress, if the proper bucket and site variables are defined

    If the package should not be published, add a 'Redistribution'  Term to the root level
    of the metadata. It can take two values:

        "hidden": publish to S3, but not wordpress
        "private": Don't publish to either S3 or Wordpress

    """
    wp_site = c.metapack.wp_site or wp_site

    groups = c.metapack.groups or groups
    tags = c.metapack.tags or tags

    group_flags = ' '.join([f"-g{g}" for g in groups])
    tag_flags = ' '.join([f"-t{t}" for t in tags])

    pkg = open_package('./metadata.csv')

    redist = pkg.find_first_value('Root.Redistribution')
    name = pkg.name

    s3(c, s3_bucket=s3_bucket)

    if redist in ('private', 'hidden'):
        print(f"⚠️  Package {name} is {redist}; won't publish to wordpress")
    elif wp_site:
        c.run(f"mp wp -s {wp_site} {group_flags} {tag_flags} -p", pty=True)

    if redist not in ('private', 'hidden') and not s3_bucket and not wp_site:
        print("⚠️  Neither s3 bucket nor wp site config specified; nothing to do")


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
def install(c, dest):
    p = Path('.').joinpath('_packages', '.last_build')

    if not Path(dest).exists():
        Path(dest).mkdir(parents=True)

    if p.exists():

        # Get the name of the File package
        lb = p.read_text().strip()
        u = parse_app_url(lb)
        fp = u.fspath.parent

        # Make them concrete
        zp = Path(fp.with_suffix('.zip'))
        fp = Path(fp)

        if fp.exists():
            c.run(f"rsync -rva {str(fp)} '{str(dest)}/'")

        if zp.exists():
            c.run(f"rsync -rva {str(zp)} '{str(dest)}/'")


@task
def clean(c):
    c.run('rm -rf _packages')


@task
def pip(c):
    """Install any python packages specified in a requirements.txt file"""

    if Path('requirements.txt').exists():
        c.run('pip install -r requirements.txt')


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


@task
def dummy(c):
    """A Dummy tasks for overridding other tasks, such as publish when you dont want
    a dataset published"""
    pass


# Pull in metapack configuration

def merge_config(key):
    from pathlib import Path
    import yaml
    metapack_config = get_config().get('invoke', {})

    p = Path('../invoke.yaml')

    if p.exists():
        with p.open() as f:
            iconfig = yaml.safe_load(f)

        try:
            return iconfig['metapack'][key]
        except (KeyError, TypeError):
            pass

    if metapack_config.get(key):
        return metapack_config.get(key)

    else:
        return None


ns = None


# This is implemented as a function with a global ns so it can be re-set in
# loops in .collection, so, for instance, build() tasks set in one directory
# don't persist into another.
def make_ns():
    global ns
    ns = Collection(build, s3, publish, make, config, clean, pip, install)
    ns.configure(
        {
            'metapack':
                {
                    's3_bucket': merge_config('s3_bucket'),
                    'wp_site': merge_config('wp_site'),
                    'groups': merge_config('groups'),
                    'tags': merge_config('tags')
                }
        }
    )


make_ns()
