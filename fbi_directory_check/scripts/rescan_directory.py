# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '19 Jul 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

import os
import argparse
from fbi_directory_check.core.rabbit_connection import RabbitMQConnection
from fbi_directory_check.utils.constants import DepositAction
from fbi_directory_check.utils import walk_storage_links, valid_path


def get_args():
    """
    Command line arguments
    :return:
    """

    default_config = os.path.join(os.path.dirname(__file__), '../conf/index_updater.ini')

    parser = argparse.ArgumentParser(description='Submit directories to be re-scanned.')
    parser.add_argument('dir', type=str, help='Directory to scan')
    parser.add_argument('-r', dest='recursive', action='store_true',
                        help='Recursive. Will include all directories below this point as well')
    parser.add_argument('--no-files', dest='nofiles', action='store_true', help='Ignore files')
    parser.add_argument('--no-dirs', dest='nodirs', action='store_true', help='Ignore directories')
    parser.add_argument('--conf', type=str, default=default_config, help='Optional path to configuration file')

    return parser.parse_args()


def main():

    args = get_args()

    output_files = []
    output_directories = []

    # Check path is valid
    valid_path(args.dir)

    # Get the full path
    abs_root = os.path.abspath(args.dir)

    # Submit items to rabbit queue for re-scan
    rabbit_connection = RabbitMQConnection(args.conf)

    # Add the root directory
    msg = rabbit_connection.create_message(abs_root, DepositAction.MKDIR)
    rabbit_connection.publish_message(msg)

    # If -r flag, walk the whole tree, if not walk only the immediate directory
    if args.recursive:
        max_depth = None
    else:
        max_depth = 1

    for root, dirs, files in walk_storage_links(abs_root, max_depth=max_depth):

        # Add directories
        if not args.nodirs:
            for _dir in dirs:
                msg = rabbit_connection.create_message(os.path.join(root, _dir), DepositAction.MKDIR)
                rabbit_connection.publish_message(msg)

        # Add files
        if not args.nofiles:
            for file in files:
                msg = rabbit_connection.create_message(os.path.join(root, file), DepositAction.DEPOSIT)
                rabbit_connection.publish_message(msg)

                if os.path.basename(file) == README:
                    msg = rabbit_connection.create_message(os.path.join(root, file), DepositAction.README)
                    rabbit_connection.publish_message(msg)


if __name__ == '__main__':
    main()
