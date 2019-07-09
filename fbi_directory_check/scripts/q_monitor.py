# encoding: utf-8
"""

"""
__author__ = 'Richard Smith'
__date__ = '09 Jul 2019'
__copyright__ = 'Copyright 2018 United Kingdom Research and Innovation'
__license__ = 'BSD - see LICENSE file in top-level package directory'
__contact__ = 'richard.d.smith@stfc.ac.uk'

import os
from six.moves.configparser import RawConfigParser
import persistqueue


def main():
    base = os.path.dirname(__file__)
    default_config = os.path.join(base, '../conf/index_updater.ini')

    conf = RawConfigParser()
    conf.read(default_config)

    db_location = conf.get('local-queue', 'queue-location')

    # Setup local queues
    manual_queue = persistqueue.SQLiteAckQueue(
        os.path.join(db_location, 'priority')
    )
    bot_queue = persistqueue.SQLiteAckQueue(
        os.path.join(db_location, 'bot')
    )

    manual_qsize = manual_queue._count()
    bot_qsize = bot_queue._count()

    print ("Crawler Queue Size: {} User Submitted Queue Size: {}".format(bot_qsize, manual_qsize))


if __name__ == '__main__':
    main()
