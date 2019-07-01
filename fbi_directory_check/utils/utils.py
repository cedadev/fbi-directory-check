# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '18 Jun 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

def get_line_in_file(filepath, index):
    """
    Given a file path and and line number
    Return the line at that line number.
    Will return either the line or an empty string if you exceed the boundary of the file
    :param filepath: Path to the file to read
    :param index: Line number
    :return: The line at that index. Either has content or empty string
    """

    with open(filepath) as reader:

        for _ in range(index):
            line = reader.readline()

        return line