# encoding: utf-8
"""
Reads directories off a queue and checks elasticsearch to make sure that the filesystem and index are in harmony
"""
__author__ = 'Richard Smith'
__date__ = '04 Jun 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

# TODO: Make sure can handler where files are on tape

import persistqueue
from six.moves.configparser import RawConfigParser
from six.moves.configparser import ConfigParser
import os
from fbi_directory_check.utils import get_line_in_file
import requests
import logging
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
import argparse
from os.path import normpath
from datetime import datetime
from fbi_directory_check.utils.constants import DEPOSIT, REMOVE, MKDIR, RMDIR, README
import pika
from hashlib import sha1

logger = logging.getLogger()

# Set level of logging for elasticsearch higher to reduce output
elastic_logger = logging.getLogger('elasticsearch')
elastic_logger.setLevel(logging.WARNING)


class ElasticsearchConsistencyChecker(object):

    def __init__(self):
        base = os.path.dirname(__file__)
        self.default_config = os.path.join(base, '../conf/index_updater.ini')

        self.conf = RawConfigParser()
        self.conf.read(self.default_config)

        # Load queue params to object
        self._load_queue_params()

        # Setup local queues
        self.manual_queue = persistqueue.SQLiteAckQueue(
            os.path.join(self.db_location, 'priority'),
            multithreading=True
        )
        self.bot_queue = persistqueue.SQLiteAckQueue(
            os.path.join(self.db_location, 'bot'),
            multithreading=True
        )

        # Create Elasticsearch connection
        self.es = Elasticsearch([self.conf.get('elasticsearch', 'es-host')], timeout=60, retry_on_timeout=True)
        self.rabbit_connect()

        self.spot_progress = self._get_spot_progress()

        # Setup logging
        logging_level = self.conf.get('logging', 'log-level')
        logger.setLevel(getattr(logging, logging_level.upper()))

        # Add formatting
        ch = logging.StreamHandler()
        ch.setLevel(getattr(logging, logging_level.upper()))
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)

        logger.addHandler(ch)

    def _load_queue_params(self):

        self.db_location = self.conf.get('local-queue', 'queue-location')

        self.spot_file = os.path.join(self.db_location, 'spot_file.txt')
        self.progress_file = os.path.join(self.db_location, 'spot_progress.txt')

    def _get_spot_progress(self):
        """
        Set the line to read from the spot file on initialisation

        :return: int
        """

        if os.path.exists(self.progress_file):
            with open(self.progress_file) as reader:
                line = reader.readline()

            if line:
                return int(line.strip())

        return 0

    def _update_spot_progress(self):
        """
        Write the progress to file so that it persists if the main process dies
        """
        self.spot_progress += 1
        logger.debug('Spot progress: {}'.format(self.spot_progress))

        with open(self.progress_file, 'w') as writer:
            writer.write(str(self.spot_progress))

    def _download_spot_conf(self):
        """
        Download spot configuration file and write to disk
        """

        url = self.conf.get('local-queue', 'spot-url')

        r = requests.get(url)

        with open(self.spot_file, 'w') as writer:
            writer.write(r.text)

        self.spot_progress = 0

    def rabbit_connect(self):
        """
        Start Pika connection to server. This is run in each thread.

        :return: pika channel
        """

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
        channel.queue_declare(queue=rabbit_queue, auto_delete=True)

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

    def get_query(self, index, directory):

        depth = len(directory.split('/'))

        queries = {
            'ceda-dirs': {
                'query': {
                    'bool': {
                        'must': [
                            {
                                'prefix': {
                                    'path.keyword': directory
                                }
                            }
                        ],
                        'filter': {
                            "range": {
                                "depth": {
                                    "gte": depth -1,
                                    "lte": depth
                                }
                            }
                        }
                    }
                }
            },
            'ceda-fbi': {
                'query': {
                    'term': {
                        'info.directory': directory
                    }
                }
            }
        }

        return queries.get(index)

    def compare_ceda_fbi(self, item, listing):

        # setup empty deletion set
        delete_es = set()

        results = scan(self.es, query=self.get_query('ceda-fbi', item), index='ceda-fbi', scroll='1m')
        result_set = {os.path.join(
            result['_source']['info']['directory'], result['_source']['info']['name']) for result
            in results}

        file_set = {file for file in listing if os.path.isfile(file)}

        # Check if a '00FILES_ON_TAPE file exists
        files_on_tape = any(os.path.basename(file) == '00FILES_ON_TAPE' for file in file_set)

        # Get file in file_set not in ES (Need to add to ES)
        add_es = file_set - result_set

        # Turn off strict checking if there are files on tape as the live listing would
        # try to delete entries in the index that are stored on tape
        if not files_on_tape:
            # Get files in ES not in file_set (Need to delete from ES)
            delete_es = result_set - file_set

        logger.info('{} files to add to ES {} files to delete from ES'.format(len(add_es), len(delete_es)))
        logger.debug('Files to add: {}\n Files to remove {}'.format(add_es, delete_es))

        # Generate messages for pika queue
        for file in add_es:
            msg = self.create_message(file, DEPOSIT)
            self.publish_message(msg)

        for file in delete_es:
            msg = self.create_message(file, REMOVE)
            self.publish_message(msg)

    def compare_ceda_dirs(self, item, listing):

        # Query elasticsearch for matches to the item directory
        results = scan(self.es, query=self.get_query('ceda-dirs', item), index='ceda-dirs', scroll='1m')

        result_set = {result['_source']['path'] for result in results}

        # Build a set of directories from the file system
        dir_set = {normpath(_dir) for _dir in listing if os.path.isdir(_dir)}

        # Add item to comparison set
        dir_set.add(item)

        # Get dirs in dir_set not in ES (Need to add to ES)
        add_es = dir_set - result_set

        # Get dirs in ES not in dir_set (Need to delete from ES)
        delete_es = result_set - dir_set

        logger.info('{} dirs to add to ES {} dirs to delete from ES'.format(len(add_es), len(delete_es)))
        logger.debug('Dirs to add: {}\n Dirs to remove {}'.format(add_es, delete_es))

        # Generate messages for pika queue
        for file in add_es:
            msg = self.create_message(file, MKDIR)
            self.publish_message(msg)

        for file in delete_es:
            msg = self.create_message(file, RMDIR)
            self.publish_message(msg)

        # Check if there are any 00README files in this dir
        for file in listing:
            if os.path.basename(file) == '00README':
                msg = self.create_message(file, README)
                self.publish_message(msg)

    def process_queue(self, queue):
        """
        Perform action on the queue and acknowledge when done

        :param queue: queue name
        """

        q = getattr(self, queue)

        item = q.get()
        logger.info(item)

        if os.path.isdir(item):

            # Get list of files and directories
            listing = [os.path.join(item, file) for file in os.listdir(item)]
            self.compare_ceda_fbi(item, listing)
            self.compare_ceda_dirs(item, listing)

        q.ack(item)

    def get_next_spot(self):
        """
        Get the next spot to add to the bot queue

        :return: Next spot
        """

        # Download the configuration if it does not exist
        if not os.path.exists(self.spot_file):
            logger.debug('Spot file does not exist. Downloading...')
            self._download_spot_conf()

        # Increment spot_progress to retrieve next line
        self._update_spot_progress()

        # Get the line
        line = get_line_in_file(self.spot_file, self.spot_progress)

        if line:
            if line.strip():
                spot, path = line.strip().split()
                logger.debug('Loading spot: {}'.format(path))
            else:
                # If the line is just a \n character, get the next line.
                path = self.get_next_spot()


        else:
            # Reached EOF. Download new file
            logger.info('Reached end of spot file. Downloading new spot file')
            self._download_spot_conf()
            self._update_spot_progress()

            # Get first line
            line = get_line_in_file(self.spot_file, self.spot_progress)
            spot, path = line.strip().split()
            logger.debug('Loading spot: {}'.format(path))

        return path

    def add_dirs_to_queue(self, path):
        """
        Walks a directory tree, given a path and adds the directories to the bot queue
        """
        if not os.path.exists(path):
            logger.error('Path not found: {}'.format(path))

        for root, dirs, _ in os.walk(path):
            abs_root = os.path.abspath(root)

            for dir in dirs:
                self.bot_queue.put(os.path.join(abs_root, dir))

    def consume(self, dev=False):
        """
        Begins the main process of consuming the jobs
        
        :param dev: Flag to turn off the crawler activities
        """

        manual_qsize = self.manual_queue._count()
        bot_qsize = self.bot_queue._count()

        if manual_qsize:
            self.process_queue('manual_queue')

        elif bot_qsize:
            self.process_queue('bot_queue')

        if bot_qsize == 0 and not dev:
            logger.info('Bot queues empty, retrieving next spot.')
            spot = self.get_next_spot()
            self.add_dirs_to_queue(spot)

    @classmethod
    def main(cls):

        parser = argparse.ArgumentParser(description='Check directories with the elasticsearch indices to maintain'
                                                     'consistency between the archive and the indices')

        parser.add_argument('--dev', action='store_true',
                            help='Disables the crawler to reduce number of events to process')

        args = parser.parse_args()

        checker = cls()

        print("Ready")
        while True:

            try:
                checker.consume(dev=args.dev)

            except pika.exceptions.StreamLostError as e:
                logger.error('Connection lost, reconnecting', exc_info=e)
                checker.rabbit_connect()

            except KeyboardInterrupt:
                break

            except Exception as e:
                logger.error(e, exc_info=True)
                break


if __name__ == '__main__':
    ElasticsearchConsistencyChecker.main()
