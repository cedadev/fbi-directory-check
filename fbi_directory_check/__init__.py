# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '18 Jun 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

# Logger setup
import logging

logging.basicConfig(level=logging.DEBUG)
logstream = logging.StreamHandler()

formatter = logging.Formatter('%(levelname)s [%(name)s]: %(message)s')
logstream.setFormatter(formatter)