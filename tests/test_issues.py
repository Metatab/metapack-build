# Copyright (c) 2017 Civic Knowledge. This file is licensed under the terms of the
# Revised BSD License, included in this distribution as LICENSE

"""

"""

import unittest
import warnings

from metapack import Downloader
from support import MetapackTest

warnings.filterwarnings("ignore", category=DeprecationWarning)

downloader = Downloader()


class TestIssues(MetapackTest):

    def test_s3_upload(self):
        from metapack_build.package.s3 import S3Bucket
        from rowgenerators import parse_app_url

        pp = 's3://library.metatab.org/'

        pp = parse_app_url(pp)

        bucket = S3Bucket(pp, acl='public-read')

        access_url = bucket.write('foobar', '000foobar.txt', force=True)

        print('!!!', access_url, bucket.last_reason)


if __name__ == '__main__':
    unittest.main()
