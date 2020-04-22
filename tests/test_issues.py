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

    def test_bad_load_of_nulls(self):
        pass


if __name__ == '__main__':
    unittest.main()
