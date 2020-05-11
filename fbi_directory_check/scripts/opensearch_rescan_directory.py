# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '04 May 2020'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

import pika
import argparse
from configparser import RawConfigParser
from datetime import datetime
from fbi_directory_check.utils.constants import DEPOSIT
from fbi_directory_check.utils import walk_storage_links


class RabbitMQConnection(object):
    """Handles the connection with the RabbitMQ service"""

    def __init__(self, config):
        self.conf = RawConfigParser()
        self.conf.read(config)

        # Get the username and password for rabbit
        rabbit_user = self.conf.get('server', 'user')
        rabbit_password = self.conf.get('server', 'password')

        # Get the opensearch exchange
        self.opensearch_exchange = self.conf.get('server', 'opensearch_exchange')

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
        channel.exchange_declare(exchange=self.opensearch_exchange, exchange_type='topic')

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

        return {
            'datetime': time,
            'filepath': path,
            'action': action.upper(),
            'filesize': 0,
            'message': ''
        }

    def publish_message(self, msg, routing_key=''):
        self.channel.basic_publish(
            exchange=self.opensearch_exchange,
            routing_key=routing_key,
            body=msg
        )


def get_args():
    parser = argparse.ArgumentParser(description='Submit items to be re-scanned for opensearch.')

    parser.add_argument('dir', help='Directory to add to scan', type=str)
    parser.add_argument('-r', dest='recursive', action='store_true',
                        help='Recursive scan. Will include all subdirectories.')
    parser.add_argument('-t', '--tag-only', dest='tag', action='store_true',
                        help='Add this flag to only send to tag queue. '
                             'Use this if the files are present but need to rescan for opensearch tags.')
    parser.add_argument('--conf', help='Path to configuration file')

    return parser.parse_args()


def main():

    args = get_args()

    output_files = []

    if not os.path.exists(args.dir):
        raise OSError(f'{ars.dir} is not accessible')

    # Check for tags only flag
    if args.tag:
        routing_key='opensearch.tagger.cci'
    else:
        routing_key=''

    # Get the full path
    abs_root = os.path.abspath(args.dir)

    if args.recursive():
        for root, dirs, files in walk_storage_links(abs_root):

            for file in files:
                output_files.append(os.path.join(root, file))

    else:
        for item in os.listdir(abs_root):
            item = os.path.join(abs_root, item)

            if os.path.isfile(item):
                output_files.append(item)

    print(f'Found {len(output_files)} files to submit')
    print('Submitting...')
    # Submit items to rabbit queue for processing
    rabbit_connection = RabbitMQConnection(args.conf)

    for file in output_files:
        msg = rabbit_connection.create_message(file, DEPOSIT)
        rabbit_connection.publish_message(msg, routing_key=routing_key)


if __name__ == '__main__':
    main()