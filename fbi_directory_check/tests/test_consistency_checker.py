# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '05 Jun 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'


import unittest
import os
from shutil import rmtree
from fbi_directory_check.scripts.consistency_checker import ElasticsearchConsistencyChecker

#################################################
#                                               #
#                   Functions                   #
#                                               #
#################################################


def join(base, append):
    return os.path.join(base, append)

#################################################
#                                               #
#                    Tests                      #
#                                               #
#################################################


class TestConsistencyChecker(unittest.TestCase):

    test_dir_name = 'test_dirs'
    test_directory = join(os.path.dirname(__file__), test_dir_name)

    def get_test_path(self, path):
        ending = path.split(self.test_dir_name)[1][1:]
        return join(self.test_dir_name, ending)

    @classmethod
    def setUpClass(cls):

        cls.spots = []

        for i in range(1,4):
            path = join(cls.test_directory, 'dir{}'.format(i))
            os.makedirs(path)
            cls.spots.append(path)

    def setUp(self):
        self.checker = ElasticsearchConsistencyChecker()

    def tearDown(self):
        "Clear up databases and spot file"
        rmtree(self.checker.db_location)

    def test_spot_progress(self):
        self.assertEqual(self.checker.spot_progress, 0)

    def test_update_spot_progress(self):
        self.checker._update_spot_progress()
        self.assertEqual(self.checker.spot_progress, 1)
        self.assertTrue(os.path.exists(self.checker.progress_file))

    def test_download_spot_conf(self):
        self.checker._download_spot_conf()
        self.assertEqual(self.checker.spot_progress, 0)
        self.assertTrue(os.path.exists(self.checker.spot_file))

    def test_get_next_spot(self):

        # Setup the spot file
        with open(self.checker.spot_file,'w') as writer:
            writer.writelines(map(lambda x: 'spot {}\n'.format(x), self.spots))

        for _dir in self.spots:
            spot = self.checker.get_next_spot()
            self.assertEqual(spot, _dir)

    def test_spot_file_rollover(self):

        # Setup the spot file
        with open(self.checker.spot_file,'w') as writer:
            writer.writelines(map(lambda x: 'spot {}\n'.format(x), self.spots))

        for _dir in self.spots:
            self.checker.get_next_spot()

        # Check what happens when the file rolls over
        # It SHOULD download the new spot config from cedaarciveapp and so the new path
        # will be linked to the ceda archive
        spot = self.checker.get_next_spot()
        self.assertTrue(spot.startswith(('/badc','/neodc')))

    def test_add_dirs_to_queue(self):

        self.checker.add_dirs_to_queue(self.test_directory)

        for _ in self.spots:
            item = self.checker.bot_queue.get()
            self.assertTrue(self.get_test_path(item) in self.spots)

    def test_create_message(self):
        filename = '/path/to/a/file.txt'
        action = 'DEPOSIT'

        message = self.checker.create_message(filename, action)

        split_message = message.split(':')
        self.assertEqual(split_message[3], filename)
        self.assertEqual(split_message[4], action)


    @classmethod
    def tearDownClass(cls):
        rmtree(cls.test_directory)


if __name__ == '__main__':
    print('In order for test_add_dirs to work, you need to run this from the test directory...')
    unittest.main()