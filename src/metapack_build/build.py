# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE

"""


"""

from metapack.cli.core import prt
from metatab import DEFAULT_METATAB_FILE

from .package import (CsvPackageBuilder, ExcelPackageBuilder,
                      FileSystemPackageBuilder, ZipPackageBuilder)


def _exec_build(p, package_root, force, nv_name, extant_url_f, post_f):
    from metapack import MetapackUrl

    if force:
        reason = 'Forcing build'
        should_build = True
    elif p.is_older_than_metadata():
        reason = 'Metadata is younger than package'
        should_build = True
    elif not p.exists():
        reason = "Package doesn't exist"
        should_build = True
    else:
        reason = 'Metadata is older than package'
        should_build = False

    if should_build:
        prt("Building {} package ({})".format(p.type_code, reason))
        url = p.save()
        prt("Package ( type: {} ) saved to: {}".format(p.type_code, url))
        created = True
    else:
        prt("Not building {} package ({})".format(p.type_code, reason))

    if not should_build and p.exists():
        created = False
        url = extant_url_f(p)

    post_f()

    if nv_name:
        p.move_to_nv_name()

    return p, MetapackUrl(url, downloader=package_root.downloader), created


def make_excel_package(file, package_root, cache, env, force, nv_name=None, nv_link=False):
    assert package_root

    p = ExcelPackageBuilder(file, package_root, callback=prt, env=env)

    return _exec_build(p,
                       package_root, force, nv_name,
                       lambda p: p.package_path.path,
                       lambda: p.create_nv_link() if nv_link else None)


def make_zip_package(file, package_root, cache, env, force, nv_name=None, nv_link=False):
    assert package_root

    p = ZipPackageBuilder(file, package_root, callback=prt, env=env)

    return _exec_build(p,
                       package_root, force, nv_name,
                       lambda p: p.package_path.path,
                       lambda: p.create_nv_link() if nv_link else None)


def make_filesystem_package(file, package_root, cache, env, force, nv_name=None, nv_link=False, reuse_resources=False):
    from os.path import join

    assert package_root

    p = FileSystemPackageBuilder(file, package_root, callback=prt, env=env, reuse_resources=reuse_resources)

    return _exec_build(p,
                       package_root, force, nv_name,
                       lambda p: join(p.package_path.path.rstrip('/'), DEFAULT_METATAB_FILE),
                       lambda: p.create_nv_link() if nv_link else None)


def make_csv_package(file, package_root, cache, env, force, nv_name=None, nv_link=False):
    assert package_root

    p = CsvPackageBuilder(file, package_root, callback=prt, env=env)

    return _exec_build(p,
                       package_root, force, nv_name,
                       lambda p: p.package_path.path,
                       lambda: p.create_nv_link() if nv_link else None)
