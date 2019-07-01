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
from fbi_directory_check.utils import query_yes_no
import persistqueue
from six.moves import configparser
import fileinput


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
                                                 'There are 3 usage options:\n'
                                                 '  1. Submit a single directory for checking\n'
                                                 '  2. Submit a tree by providing the -r flag\n'
                                                 '  3. Pipe output from file or some other command\n')

    parser.add_argument('dir', type=str, help='Path to submit to consistency checker')
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

    # Check if there is input on stdin
    if sys.stdin.isatty:

        if check_path(args.dir):

            directories.append(args.dir)

            if args.recursive:
                for root, dirs, _ in os.walk(args.dir):
                    abs_root = os.path.abspath(root)

                    for dir in dirs:
                        directories.append(os.path.join(abs_root, dir))
        else:
            raise NotADirectoryError('{} is not a directory'.format(args.dir))

    else:
        for line in fileinput.input():
            if check_path(line.strip()):
                directories.append(line.strip())
            else:
                raise NotADirectoryError('{} is not a directory'.format(args.dir))

    print('Found {} directories. Submitting...'.format(len(directories)))

    for _dir in directories:
        queue.put(_dir)


if __name__ == '__main__':
    main()
