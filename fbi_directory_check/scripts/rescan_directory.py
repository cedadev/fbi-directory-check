# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '19 Jul 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

import argparse
import glob
import json
import logging
import os
import re
from datetime import datetime
from typing import Union

import pika
from six.moves.configparser import RawConfigParser

from fbi_directory_check import logstream
from fbi_directory_check.utils import (check_timeout, set_verbose,
                                       walk_storage_links)
from fbi_directory_check.utils.constants import DEPOSIT, MKDIR, README, SYMLINK

logger = logging.getLogger(__name__)
logger.addHandler(logstream)
logger.propagate = False


class RabbitMQConnection:
    """
    Handles the connection with the RabbitMQ service.
    Takes a config file as input with the following expected content:
    
    server:
      name:
      user:
      password:
      exchange:
      exchange_type:
      vhost:
    
    """

    def __init__(self, config):
        self.conf = RawConfigParser()
        self.conf.read(config)

        # Get the username and password for rabbit
        rabbit_user = self.conf.get('server', 'user')
        rabbit_password = self.conf.get('server', 'password')

        # Get the fbi exchange
        self.exchange = self.conf.get('server','exchange')

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
        channel.exchange_declare(exchange=self.exchange, exchange_type=self.conf.get('server','exchange_type'))

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

        return json.dumps({
            'datetime': time,
            'filepath': path,
            'action': action.upper(),
            'filesize': 0,
            'message': ''
        })

    def publish_message(self, msg: str, routing_key: str = ''):
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=routing_key,
            body=msg
        )


"""
def get_dataset_filelist(dataset):
    """
    #Query Elasticsearch for the list of files in the changed dataset
    #:param dataset: path to root of dataset
    #:return: list of file paths
"""

    query = {
        "_source": {
            "includes": ["info.directory", "info.name"]
        },
        "query": {
            "match_phrase_prefix": {
                "info.directory.analyzed": dataset
            }
        }
    }

    es = CEDAElasticsearchClient()
    results = scan(es, query=query, index='opensearch-files')

    file_list = [
        os.path.join(
            item['_source']['info']['directory'],
            item['_source']['info']['name']
        ) for item in results
    ]

    return file_list
"""

def check_valid_path(path):
    """
    Check that we have been given a real directory
    :param path:
    :return: boolean
    """
    if path == '/':
        raise Exception('Cannot scan from root')

    if not bool(os.path.exists(path) and os.path.isdir(path)):
        raise OSError('{} is not a directory'.format(path))
    
class RescanDirs:

    def __init__(
            self, 
            scan_path: str,
            scan_level: int = 1,
            use_rabbit: bool = False,
            conf: str = '',
            dryrun: bool = False, 
            skip_dirs: bool = False,
            skip_files: bool = False,
            recursive: bool = False,
            file_regex: Union[str,None] = None,
            extension: str = 'nc',
            output: str = None
        ) -> None:

        if scan_path == '':
            self._init_from_args()
            return
        
        if scan_level == 1:
            # Directory level search
            check_valid_path(scan_path)

            self.scan_path = os.path.abspath(scan_path)
        else:
            self.scan_path = scan_path

        self.scan_level = scan_level
        self.use_rabbit = use_rabbit
        self.conf = conf

        # Default match any filename not starting with a . dot
        self._file_regex = file_regex
        self._extension  = extension

        self._dryrun = dryrun
        self._recursive = recursive
        self._output = output

        self.skip_dirs = skip_dirs
        self.skip_files = skip_files

        self.routing_key = 'elasticsearch_update_queue_opensearch_ingest'

    @property
    def file_regex(self):
        if self._file_regex is not None and self._extension is not None:
            regex = f'{self._file_regex}(.{self._extension})$'
            try:
                re.compile(regex)
                return regex
            except re.error:
                raise ValueError(
                    'Incompatible regex and extensions given - '
                    f'{regex} is not valid regular expression.'
                )
        if self._extension is not None:
            return f'.+?(.{self._extension})$'
        elif self._file_regex is not None:
            return self._file_regex
        else:
            return '.+'


    @property
    def max_depth(self):
        if self._recursive:
            return None
        else:
            return 1

    def _init_from_args(self):

        default_config = os.path.join(os.path.dirname(__file__), '../conf/rabbit_updater.ini')

        parser = argparse.ArgumentParser(description='Submit directories/items to be re-scanned.')
        parser.add_argument('dir', type=str, help='Directory to scan')
        parser.add_argument('-r', dest='recursive', action='store_true',
                            help='Recursive. Will include all directories below this point as well')

        parser.add_argument('-l','--scan-level',type=int, dest='scan_level',
                            help='Level of depth for scanning (1,2,3)')
        parser.add_argument('-R','--use-rabbit',dest='use_rabbit',
                            help='Deposit to rabbit queues or return list of paths')
        parser.add_argument('-v','--verbose', action='count', default=2, help='Set level of verbosity for logs')

        #parser.add_argument('--no-files', dest='nofiles', action='store_true', help='Ignore files')
        
        # Removed the ability to publish whole directories
        #parser.add_argument('--no-dirs', dest='nodirs', action='store_true', help='Ignore directories')
        parser.add_argument('--conf', type=str, default=default_config, help='Optional path to configuration file')
        parser.add_argument('--dry-run', dest='dryrun', action='store_true', help='Display log messages to screen rather than pushing to rabbit')

        parser.add_argument('-o','--output',dest='output', help='Store output list in a file.')

        parser.add_argument('--file-regex', dest='file_regex', 
                            help='Matching file regex, by default regex applies to all files not starting with "."')
        parser.add_argument('--extension', dest='extension', 
                            help='Matching files by file extension.', default='nc')
        args = parser.parse_args()

        set_verbose(args.verbose)

        self.__init__(
            args.dir,
            scan_level=args.scan_level,
            use_rabbit=args.use_rabbit,
            conf=args.conf,
            dryrun=args.dryrun,
            recursive=args.recursive,
            file_regex=args.file_regex,
            output=args.output,
            extension=args.extension
        )

    def _setup_rabbit(self):

        if not self.conf:
            raise ValueError(
                'A configuration file (--conf) must be supplied when using rabbit'
            )

        self.rabbit_connection = RabbitMQConnection(self.conf)

    def _submit_to_rabbit(self, item: str, itype = 'DEPOSIT') -> None:
        """
        Perform all operations for a specific file.
        All checks in relation to filepath should be checked
        before this stage.
        """
        logger.info(f'Depositing {item} to Rabbit')

        msg = self.rabbit_connection.create_message(item, itype) #Deposit
        self.rabbit_connection.publish_message(msg, routing_key=self.routing_key) #'opensearch.tagger.cci')

    def _determine_paths(self):
        """
        Obtain the list of filepaths to enter
        into the facet scanner.

        This is either based on a file path, gathering
        all files under a directory (with a given regex),
        or based on a submission of JSON files.
        """

        scan_files = []

        if self.scan_level == 2: # All files under a directory
            logger.info('Scanning directories')
            for root, dirs, files in walk_storage_links(self.scan_path, max_depth=self.max_depth):
                for file in files:
                    if not re.match(self.file_regex, file):
                        continue

                    scan_files.append(f'{root}/{file}')

        else:
            # Pull files from json
            logger.info(f'Scanning JSON directory: {self.scan_path}')
            scanpath = f'{os.path.abspath(self.scan_path)}/**/*.json'
            jsons = glob.glob(scanpath, recursive=True)

            total_json = len(jsons)
            for idx, file in enumerate(jsons):
                logger.info(f'Processing {file}')
                # Only want to track the changes in the JSON directory
                if not file.endswith('.json'):
                    continue

                with open(file) as reader:
                    data = json.load(reader)
                if 'datasets' not in data:
                    logger.warning(f'File {file}: missing "datasets" attribute')
                    continue
                ds = data['datasets']

                if not hasattr(ds, '__iter__'):
                    logger.warning(f'File {file}: "datasets" property is not iterable.')
                    continue

                dfiles = []
                for d in ds:
                    # Find all single files
                    dfiles = [f for f in glob.glob(f'{d}/**/*.*', recursive=True) if re.match(self.file_regex,f)]
                    scan_files += dfiles

                logger.info(f'({idx+1}/{total_json}) {len(dfiles)} datasets ({file.split("/")[-1]}) ({len(scan_files)} total)')

        return scan_files

    def scan(self) -> list:
        output_files = 0

        if self.use_rabbit:
            self._setup_rabbit()

        deposit_paths = []

        for path in self._determine_paths():
            # Note the mkdir and symlink messages are no longer
            # required as all files have been ingested separately.

            output_files += 1

            # Create symlink message for file links
            if os.path.islink(path):
                action = SYMLINK
            else:
                action = DEPOSIT

            if self._dryrun:
                logger.info(f'{action}: {path}')
                continue

            if self.use_rabbit:
                self._submit_to_rabbit(path, itype=action)
            else:
                # Do something with the paths here.
                deposit_paths.append(path)

        logger.info(f'Submitted {output_files} files')
        return deposit_paths

    def save_data(self, outdata):

        if self._output is None:
            for line in outdata:
                print(line)
            return
        
        with open(self._output,'w') as f:
            f.write('\n'.join(outdata))

def main():

    logger.info("Starting rescan check")
    if check_timeout():
        return
    logger.info("Archive access check: SUCCESS")

    r = RescanDirs('')
    if not r.use_rabbit:
        r.save_data(r.scan())
    else:
        _ = r.scan()

if __name__ == '__main__':
    main()
    

