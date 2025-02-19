# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '18 Jun 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

import asyncio
import logging
import os

from fbi_directory_check import logstream

logger = logging.getLogger(__name__)
logger.addHandler(logstream)
logger.propagate = False

def set_verbose(level: int):
    """
    Reset the logger basic config.
    """

    levels = [
        logging.WARN,
        logging.INFO,
        logging.DEBUG,
    ]

    if level >= len(levels):
        level = len(levels) - 1

    for name in logging.root.manager.loggerDict:
        lg = logging.getLogger(name)
        lg.setLevel(levels[level])

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

def environ_or_required(key):
    return (
        {'default': os.environ.get(key)} if os.environ.get(key)
        else {'required': True}
    )

def walk_storage_links(path: str, depth: int = 0, max_depth: int = None):
    """
    Used within the archive to follow links to storage pots but ignore links which are
    back within the archive and could be circular.
    :param path:
    :param depth:
    :param max_depth:
    :return:
    """
    top = os.fspath(path)
    dirs = []
    nondirs = []

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        scandir_it = os.scandir(top)
    except OSError:
        return

    if max_depth:
        if depth >= max_depth:
            return

    with scandir_it:
        while True:
            try:
                try:
                    entry = next(scandir_it)
                except StopIteration:
                    break
            except OSError as error:
                logger.error(error)
                return

            try:
                is_dir = entry.is_dir()
            except OSError:
                # If is_dir() raises an OSError, consider that the entry is not
                # a directory, same behaviour than os.path.isdir().
                is_dir = False

            if is_dir:
                dirs.append(entry.name)
            else:
                nondirs.append(entry.name)

    # Yield before recursion when going top down
    yield top, dirs, nondirs

    depth += 1
    # Recurse into sub-directories
    islink, join = os.path.islink, os.path.join
    for dirname in dirs:
        new_path = join(top, dirname)
        if islink(new_path):
            # Only follow links to storage locations
            if os.readlink(new_path).startswith('/datacentre'):
                yield from walk_storage_links(new_path, depth, max_depth)
        else:
            # If the path is not a link, recurse
            yield from walk_storage_links(new_path, depth, max_depth)

def check_timeout():

    from pathlib import Path
    from pathlib import _ignore_error as pathlib_ignore_error

    import aiofiles.os as aos

    async def path_exists(path) -> bool:
        try:
            await aos.stat(str(path))
        except OSError as e:
            if not pathlib_ignore_error(e):
                raise
            return ''
        except ValueError:
            # Non-encodable path
            return ''
        return True

    async def listfile():
        async with asyncio.timeout(10):
            await path_exists('/neodc/esacci/esacci_terms_and_conditions.txt')
    try:
        status = asyncio.run(listfile())
    except TimeoutError:
        logger.error('TIMEOUT: ESACCI Directories inaccessible')
        return True

    # If we didn't get a timeout error, can now perform a standard check.
    if not os.path.isfile('/neodc/esacci/esacci_terms_and_conditions.txt'):
        logger.error('INACCESSIBLE: ESACCI Directories inaccessible')
        return True
    return False