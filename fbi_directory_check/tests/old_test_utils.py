# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '10 Feb 2021'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'


import os
import unittest

from pyfakefs.fake_filesystem_unittest import TestCase

from fbi_directory_check.utils import walk_storage_links


class StorageWalkerTestCase(TestCase):
    
    def setUp(self):
        self.setUpPyfakefs()

        dirs = [
            '/test/1-1/2-1/3-1/4-1/5-1',
            '/test/1-1/2-2',
            '/test/1-2',
            '/test/1-3/2-3/3-2',
            '/test/1-4/2-4/3-3/4-2/5-2/6-1'
        ]

        # Setup the fake directory structure
        for dir in dirs:
            self.fs.create_dir(dir)

    def walk_fs(self, path, max_depth):
        output_directories = []
        output_files = []

        for root, dirs, files in walk_storage_links(path, max_depth=max_depth):
            # Add directories
            for _dir in dirs:
                output_directories.append(os.path.join(root, _dir))

            # Add files
            for file in files:
                output_files.append(os.path.join(root, file))

        return output_directories, output_files

    def test_walk_depth(self):
        """
        Check that the maximum depth returned
        is respected
        """

        start_dir = '/test'
        expected_max_depth = [1,2,4]

        for depth in expected_max_depth:
            dirs, files = self.walk_fs(start_dir, max_depth=depth)
            measured_depth = max([path.split(start_dir)[1].count('/') for path in dirs])

            self.assertEqual(measured_depth, depth)


if __name__ == '__main__':
    unittest.main()