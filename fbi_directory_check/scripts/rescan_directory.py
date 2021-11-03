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
from six.moves.configparser import RawConfigParser
from datetime import datetime
from fbi_directory_check.utils.constants import DEPOSIT, MKDIR, README, SYMLINK
import pika
from fbi_directory_check.utils import walk_storage_links


class RabbitMQConnection(object):

    def __init__(self, config):
        self.conf = RawConfigParser()
        self.conf.read(config)

        # Get the username and password for rabbit
        rabbit_user = self.conf.get('server', 'user')
        rabbit_password = self.conf.get('server', 'password')

        # Get the fbi exchange
        self.fbi_exchange = self.conf.get('server','fbi_exchange')

        # Start the rabbitMQ connection
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                self.conf.get('server', 'name'),
                credentials=pika.PlainCredentials(rabbit_user, rabbit_password),
                virtual_host=self.conf.get('server', 'vhost'),
                heartbeat=300
            )
        )

        # Create a new channel
        channel = connection.channel()

        # Declare relevant exchanges
        channel.exchange_declare(exchange=self.fbi_exchange, exchange_type='fanout')

        self.channel = channel

    @staticmethod
    def create_message(path, action):
        """
        Create message to add to rabbit queue. Message matches format of deposit logs.
        date_time:path:action:size:message

        :param path: Full logical path to file
        :param action: Action constant
        :return: string which matches deposit log format
        """
        time = datetime.now().isoformat(sep='-')

        return '{}:{}:{}::'.format(time, path, action.upper())

    def publish_message(self, msg):
        self.channel.basic_publish(
            exchange=self.fbi_exchange,
            routing_key='',
            body=msg
        )


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
    parser.add_argument('--dry-run', dest='dryrun', action='store_true', help='Display log messages to screen rather than pushing to rabbit')

    return parser.parse_args()


def valid_path(path):
    """
    Check that we have been given a real directory
    :param path:
    :return: boolean
    """
    if not bool(os.path.exists(path) and os.path.isdir(path)):
        raise OSError('{} is not a directory'.format(path))

    if path == '/':
        raise  Exception('Cannot scan from root')


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
    msg = rabbit_connection.create_message(abs_root, MKDIR)

    if args.dryrun:
        print(msg)
    else:
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
                path = os.path.join(root, _dir)

                if os.path.islink(path):
                    msg = rabbit_connection.create_message(path, SYMLINK)
                else:
                    msg = rabbit_connection.create_message(path, MKDIR)

                if args.dryrun:
                    print(msg)
                else:
                    rabbit_connection.publish_message(msg)

        # Add files
        if not args.nofiles:
            for file in files:
                path = os.path.join(root, file)

                # Create symlink message for file links
                if os.path.islink(path):
                    msg = rabbit_connection.create_message(path, SYMLINK)
                else:
                    msg = rabbit_connection.create_message(path, DEPOSIT)

                if args.dryrun:
                    print(msg)
                else:
                    rabbit_connection.publish_message(msg)

                if os.path.basename(file) == README:
                    msg = rabbit_connection.create_message(path, README)

                    if args.dryrun:
                        print(msg)
                    else:
                        rabbit_connection.publish_message(msg)


if __name__ == '__main__':
    main()