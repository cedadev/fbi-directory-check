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
from fbi_directory_check.utils.constants import DEPOSIT, MKDIR, README
import pika


class RabbitMQConnection(object):

    def __init__(self, config):
        self.conf = RawConfigParser()
        self.conf.read(config)

        # Get the username and password for rabbit
        rabbit_user = self.conf.get('server', 'user')
        rabbit_password = self.conf.get('server', 'password')

        rabbit_queue = self.conf.get('server', 'queue')

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

        # Declare queue
        channel.queue_declare(queue=rabbit_queue, auto_delete=False)

        self.channel = channel
        self.rbq = rabbit_queue

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
            exchange='',
            routing_key=self.rbq,
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

    return parser.parse_args()


def valid_path(path):
    """
    Check that we have been given a real directory
    :param path:
    :return: boolean
    """
    return bool(os.path.exists(path) and os.path.isdir(path))


def main():

    args = get_args()

    output_files = []
    output_directories = []

    if not valid_path(args.dir):
        raise OSError('{} is not a directory'.format(args.dir))

    # Get the full path
    abs_root = os.path.abspath(args.dir)

    # Add the root directory
    output_directories.append(abs_root)

    # If -r flag, walk the tree
    if args.recursive:

        for root, dirs, files in os.walk(abs_root):

            # Add directories
            for _dir in dirs:
                output_directories.append(os.path.join(root, _dir))

            # Add files
            for file in files:
                output_files.append(os.path.join(root, file))

    # Just add the contents of the specified directory
    else:
        for item in os.listdir(abs_root):

            item = os.path.join(abs_root, item)

            if os.path.isdir(item):
                output_directories.append(os.path.join(abs_root, item))

            elif os.path.isfile(item):
                output_files.append(os.path.join(abs_root, item))

    # Submit items to rabbit queue for re-scan
    rabbit_connection = RabbitMQConnection(args.conf)

    if not args.nodirs:
        for directory in output_directories:
            msg = rabbit_connection.create_message(directory, MKDIR)
            rabbit_connection.publish_message(msg)

    if not args.nofiles:
        for file in output_files:
            msg = rabbit_connection.create_message(file, DEPOSIT)
            rabbit_connection.publish_message(msg)

            if os.path.basename(file) == README:
                msg = rabbit_connection.create_message(file, README)
                rabbit_connection.publish_message(msg)


if __name__ == '__main__':
    main()