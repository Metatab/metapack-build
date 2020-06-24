# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# MIT License, included in this distribution as LICENSE

"""
"""
import os

from metapack import MetapackPackageUrl, MetapackUrl, open_package
from metapack.cli.core import find_packages, prt
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
    """Make a normal CSV package, with links into the local filesystem package.
    These packages aren't particularly useful"""

    assert package_root

    p = CsvPackageBuilder(file, package_root, callback=prt, env=env)

    return _exec_build(p,
                       package_root, force, nv_name,
                       lambda p: p.package_path.path,
                       lambda: p.create_nv_link() if nv_link else None)


class S3CsvPackageBuilder(CsvPackageBuilder):

    def __init__(self, bucket, source_package, package_root=None, dist_urls=[], callback=None, env=None):
        from metapack.package import Downloader

        self.source_package = source_package
        self.bucket = bucket

        u = MetapackUrl(source_package.access_url, downloader=Downloader.get_instance())

        resource_root = u.dirname().as_type(MetapackPackageUrl)

        pu = MetapackUrl(source_package.private_access_url, downloader=Downloader.get_instance())

        self.private_resource_root = pu.dirname().as_type(MetapackPackageUrl)

        super().__init__(u, package_root, resource_root, callback, env)

        self.dist_urls = list(dist_urls)  # don't alter the input variable

        self.dist_urls.append(self.bucket.private_access_url(self.cache_path))  # For the S3: url for the S3 package
        self.dist_urls.append(self.bucket.access_url(self.cache_path))

        self.set_distributions(self.dist_urls)

    def _load_resource(self, source_r, abs_path=False):
        r = self.doc.resource(source_r.name)

        r.new_child('S3Url', self.private_resource_root.join(r.url).inner)

        r.url = self.resource_root.join(r.url).inner


def create_s3_csv_package(m, dist_urls, fs_p, ):
    """Create an S3 version of the csv file"""

    p = S3CsvPackageBuilder(m.bucket, fs_p, m.package_root, dist_urls)

    csv_url = p.save()

    # Write the new CSV file to S3

    with open(csv_url.path, mode='rb') as f:

        access_url = m.bucket.access_url(p.cache_path)

        m.bucket.write(f.read(), csv_url.target_file, m.acl)

        if m.bucket.last_reason:
            # Ugly encapsulation-breaking hack.
            fs_p.files_processed += [[*m.bucket.last_reason, access_url, '/'.join(csv_url.path.split(os.sep)[-2:])]]

    # Create an alternative url with no version number, so users can get the
    # most recent version
    with open(csv_url.path, mode='rb') as f:

        csv_non_ver_url = csv_url.join_dir("{}.{}".format(m.doc.nonver_name, csv_url.target_format))

        m.bucket.write(f.read(), csv_non_ver_url.target_file, m.acl)

        s3_path = csv_non_ver_url.path.split(os.sep)[-1]

        nv_access_url = m.bucket.access_url(s3_path)

        if m.bucket.last_reason:
            # Ugly encapsulation-breaking hack.
            fs_p.files_processed += [[*m.bucket.last_reason, nv_access_url, s3_path]]

        p.dist_urls.append(nv_access_url)  # More broken encapsulation ...

    return access_url, p.dist_urls, csv_url


def generate_packages(m):
    for ptype, purl, cache_path in find_packages(m.doc.get_value('Root.Name'), m.package_root):
        yield ptype, purl, cache_path


def find_csv_packages(m, downloader):
    """Locate the build CSV package, which will have distributions if it was generated  as
    an S3 package"""
    from metapack_build.package import CsvPackageBuilder

    pkg_dir = m.package_root
    name = m.doc.get_value('Root.Name')

    package_path, cache_path = CsvPackageBuilder.make_package_path(pkg_dir, name)

    if package_path.exists():
        r = open_package(package_path, downloader=downloader)
        return r

    pkgs = list(reversed(sorted(list((f.stat().st_ctime, f) for f in sorted(pkg_dir.fspath.glob('*.csv'))))))

    if pkgs:
        return open_package(pkgs[0][1], downloader=downloader)

    return None
