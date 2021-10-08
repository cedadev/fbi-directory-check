# encoding: utf-8
"""
Constants for use with the rabbit_indexer
"""
__author__ = 'Richard Smith'
__date__ = '07 Jun 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from enum import Enum


class DepositAction(Enum):
    """
    Enum class to hold action constants
    """
    DEPOSIT = 'DEPOSIT'
    REMOVE = 'REMOVE'
    MKDIR = 'MKDIR'
    RMDIR = 'RMDIR'
    README = '00README'


DEPOSIT = 'DEPOSIT'
REMOVE = 'REMOVE'
MKDIR = 'MKDIR'
RMDIR = 'RMDIR'
README = '00README'