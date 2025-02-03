# encoding: utf-8
__author__ = 'Daniel Westwood'
__date__ = '05 Nov 2024'
__copyright__ = 'Copyright 2024 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'daniel.westwood@stfc.ac.uk'

from fbi_directory_check.scripts.rescan_directory import RescanDirs

class TestRescan:
    def test_rescan_1(self):
        # Pull Files from json file.
        scan_path = 'fbi_directory_check/tests/rain/'
        scan_level = 1

        rd = RescanDirs(
            scan_path,
            scan_level=scan_level,
            output=None
        )

        assert len(rd.scan()) == 10
    
    def test_rescan_2(self):

        scan_path = 'fbi_directory_check/tests/rain/'
        scan_level = 2

        rd = RescanDirs(
            scan_path,
            scan_level=scan_level,
            output=None
        )

        assert len(rd.scan()) == 10

if __name__ == '__main__':
    TestRescan().test_rescan_1()
    TestRescan().test_rescan_2()