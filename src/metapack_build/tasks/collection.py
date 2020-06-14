# Copyright (c) 2020 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""
Task definitions for managing collections of packages, used with invoke
"""

import importlib.util
import os
import signal
import sys
from pathlib import Path

from invoke import Collection, UnexpectedExit, task

from metapack.cli.core import get_config


# This is needed because otherwise we get tracebacks from the bowels of
# entry_points.
def signal_handler(sig, frame):
    print('Keyboard interrupt')
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


def foreach_metapack_subdir(ordered_dirs=[]):
    """ For each iteration of the loop, change the working directory into
    a package subdirectory
    :param ordered_dirs: Directories to process first, in order.
    :return:
    """
    dirs = [d.parent for d in sorted(Path('.').glob('*/metadata.csv'))
            if str(d.parent) not in ordered_dirs]

    dirs = [Path(d) for d in ordered_dirs] + sorted(list(dirs))

    for d in dirs:
        d = d.resolve()
        print("> ", d)

        curdir = os.getcwd()

        os.chdir(d)

        yield d

        os.chdir(curdir)


def ns_foreach_task_subdir():
    """Return the invoke Collection ( ns ) for each subdir that has a tasks.py
    and a metadata.csv file"""
    for d in Path('.').glob('*/metadata.csv'):
        print("> ", d)
        d = d.parent.resolve()
        incl_path = d.joinpath('tasks.py')

        spec = importlib.util.spec_from_file_location("tasks.sp", incl_path)
        sp_tasks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sp_tasks)

        curdir = os.getcwd()

        os.chdir(d)
        try:
            yield sp_tasks.ns
        except AttributeError as e:
            if "tasks.sp" not in str(e):
                raise
        finally:
            os.chdir(curdir)


@task(default=True, optional=['force'])
def build(c, force=None):
    """Build a filesystem package."""
    for sp_ns in ns_foreach_task_subdir():
        print("-- running build in ", os.getcwd())
        sp_ns.tasks.build(c, force)


@task
def publish(c, s3_bucket=None, wp_site=None, groups=[], tags=[]):
    "Publish to s3 and wordpress, if the proper bucket and site variables are defined"
    for sp_ns in ns_foreach_task_subdir():
        try:
            sp_ns.tasks.publish(c, s3_bucket=s3_bucket, wp_site=wp_site,
                                groups=groups, tags=tags)
        except UnexpectedExit:
            pass


@task(optional=['force'])
def make(c, force=None, s3_bucket=None, wp_site=None, groups=[], tags=[]):
    """Build, write to S3, and publish to wordpress, but only if necessary"""

    for sp_ns in ns_foreach_task_subdir():
        try:
            sp_ns.tasks.make(c, force=force, s3_bucket=s3_bucket, wp_site=wp_site,
                             groups=groups, tags=tags)
        except UnexpectedExit:
            pass


@task
def install(c, dest):
    """Copy most recently build version of packages to a destination directory"""
    for sp_ns in ns_foreach_task_subdir():
        try:
            sp_ns.tasks.install(c, dest)
        except UnexpectedExit:
            pass


@task
def clean(c):
    """Build, write to S3, and publish to wordpress, but only if necessary"""

    for sp_ns in ns_foreach_task_subdir():
        try:
            sp_ns.tasks.ckean(c)
        except UnexpectedExit:
            pass


@task
def pip(c):
    """Install any python packages specified in the collection requirements.txt file
     and the requirements.txt files of the packages"""

    if Path('requirements.txt').exists():
        c.run("pip install -r requirements.txt")

    for sp_ns in ns_foreach_task_subdir():
        try:
            sp_ns.tasks.pip(c)
        except UnexpectedExit:
            pass


@task
def config(c):
    """Print invoke's configuration by running the config tasks in each subdirectory """
    for sp_ns in ns_foreach_task_subdir():
        try:
            sp_ns.tasks.config(c)
        except UnexpectedExit:
            pass


@task
def tox(c):
    """Run tox in each of the subdirectories """
    for sp_ns in foreach_metapack_subdir():
        try:
            c.run('tox')
        except UnexpectedExit:
            pass


@task
def git_update(c):
    """Run git submodule update on all git submodules"""
    c.run('git submodule update --recursive --remote')


@task
def git_status(c):
    """Run git submodule update on all git submodules"""
    c.run(f"git submodule foreach git status")


@task
def git_commit(c, message):
    """Run git commit -a  on all submodules"""
    c.run(f"git submodule foreach 'git commit -a -m \'{message}\''")


@task
def git_push(c):
    """Run git commit -a  on all submodules"""
    c.run(f"git submodule foreach git push ")


ns = Collection(build, publish, make, clean, config, pip,
                git_update, git_commit, git_status, git_push,
                tox, install)

metapack_config = (get_config() or {}).get('invoke', {})

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
