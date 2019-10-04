# encoding: utf-8
"""
Command line utility to submit directories to the consistency checker to compare the filesystem to elasticsearch indices

"""
__author__ = 'Richard Smith'
__date__ = '18 June 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

import argparse
import os
import persistqueue
from six.moves import configparser
from fbi_directory_check.utils import walk_storage_links


###############################################################
#                                                             #
#                         Classes                             #
#                                                             #
###############################################################


class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
    pass


###############################################################
#                                                             #
#                        Functions                            #
#                                                             #
###############################################################


def get_args():
    """
    Command line arguments
    :return:
    """

    default_config = os.path.join(os.path.dirname(__file__), '../conf/index_updater.ini')

    parser = argparse.ArgumentParser(description='Submit directories to be checked for consistency'
                                                 ' with the elasticsearch indices.\n'
                                                 'There are 4 usage options:\n'
                                                 '  1. Submit a single directory for checking\n'
                                                 '  2. Submit a tree by providing the -r flag\n'
                                                 '  3. Pipe output from file or some other command\n'
                                                 '  4. Submit a list from file\n')

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dir', type=str, help='Submit a single directory for checking')
    group.add_argument('--file', type=argparse.FileType('r'), help='Pipe a list using "-" or provide a file')
    parser.add_argument('-r', dest='recursive', action='store_true',
                        help='Recursive. Will include all directories below this point as well')
    parser.add_argument('--conf', type=str, default=default_config, help='Optional path to configuration file')

    return parser.parse_args()


def check_path(path):
    """
    Check that we have been given a real directory
    :param path:
    :return: boolean
    """
    return bool(os.path.exists(path) and os.path.isdir(path))


###############################################################
#                                                             #
#                          Script                             #
#                                                             #
###############################################################


def main():
    # Get arguments
    args = get_args()

    # Load configuration
    configuration = configparser.ConfigParser()
    configuration.read(args.conf)

    # Load database target
    db_location = configuration.get('local-queue', 'queue-location')
    queue = persistqueue.SQLiteAckQueue(os.path.join(db_location, 'priority'), multithreading=True)

    # Process directories
    directories = []

    if args.dir:
        if check_path(args.dir):
            abs_root = os.path.abspath(args.dir)

            if args.recursive:
                for root, dirs, _ in walk_storage_links(abs_root):
                    directories.append(root)
            else:
                directories.append(abs_root)

        else:
            raise OSError('{} is not a directory'.format(args.dir))

    elif args.file:
        with args.file as f:
            data = f.readlines()

        for line in data:
            if line.strip():
                directories.append(line.strip())

    print('Found {} directories. Submitting...'.format(len(directories)))

    for _dir in directories:
        queue.put(_dir)


if __name__ == '__main__':
    main()
