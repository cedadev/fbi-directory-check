# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '08 Oct 2021'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

from fbi_directory_check.utils.constants import DepositAction
from configparser import RawConfigParser
import pika
from datetime import datetime
import json


class RabbitMQConnection(object):

    def __init__(self, config: str):
        self.conf = RawConfigParser()
        self.conf.read(config)

        # Get the username and password for rabbit
        rabbit_user = self.conf.get('server', 'user')
        rabbit_password = self.conf.get('server', 'password')

        # Get the exchange
        self.exchange = self.conf.get('server', 'exchange')

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
        exchange_type = self.conf.get('server', 'exchange_type', fallback='fanout')

        channel.exchange_declare(exchange=self.exchange, exchange_type=exchange_type)

        self.channel = channel

    @staticmethod
    def create_message(path, action: DepositAction) -> str:
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
            'action': action.value,
            'filesize': 0,
            'message': ''
        })

    def publish_message(self, msg: str, routing_key='') -> None:
        self.channel.basic_publish(
            exchange=self.exchange,
            routing_key=routing_key,
            body=msg
        )
