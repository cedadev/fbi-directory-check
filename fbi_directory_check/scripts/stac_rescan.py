# encoding: utf-8
""" """
__author__ = "Richard Smith"
__date__ = "08 Oct 2021"
__copyright__ = "Copyright 2018 United Kingdom Research and Innovation"
__license__ = "BSD - see LICENSE file in top-level package directory"
__contact__ = "richard.d.smith@stfc.ac.uk"

import argparse
import json
import logging
import os
import re
from configparser import RawConfigParser

from fbi_directory_check import logstream
from fbi_directory_check.core.rabbit_connection import RabbitMQConnection
from fbi_directory_check.utils import valid_path, walk_storage_links

logger = logging.getLogger(__name__)
logger.addHandler(logstream)
logger.propagate = False


def get_args():
    default_config = os.path.join(os.path.dirname(__file__), "../conf/stac_updater.ini")
    parser = argparse.ArgumentParser(description="Submit paths to be re-scanned for stac.")
    parser.add_argument("dir", help="Directory to add to scan", type=str)
    parser.add_argument(
        "-t",
        dest="type",
        help="Scan type (file or dir).",
        choices=["file", "dir"],
        type=str,
    )
    parser.add_argument(
        "-r",
        dest="recursive",
        action="store_true",
        help="Recursive scan. Will include all subdirectories.",
    )
    parser.add_argument(
        "--conf",
        help="Optional path to configuration file",
        default=default_config,
    )

    return parser.parse_args()


def main():
    args = get_args()

    valid_path(args.dir)

    # Get the full path
    abs_root = os.path.abspath(args.dir)

    logger.info("Connecting to Rabbit")
    rabbit_connection = RabbitMQConnection(args.conf)

    conf = RawConfigParser()
    conf.read(args.conf)

    logging_level = conf.get("logging", "log-level")
    logger.setLevel(getattr(logging, logging_level.upper()))

    routing_key = conf.get("scan", "routing_key", fallback="item")

    regex = rf"{conf.get("scan", "regex", fallback=".*")}"

    # If -r flag, walk the whole tree, if not walk only the immediate directory
    if args.recursive:
        max_depth = None
    else:
        max_depth = 1

    file_count = 0
    dir_count = 0

    logger.info(f"Starting scan of {abs_root}")

    for root, dirs, files in walk_storage_links(abs_root, max_depth=max_depth):
        if args.type == "dir":
            for d in dirs:
                # Ignore hidden files
                if re.match(regex, d):
                    # Submit items to rabbit queue for processing during recursion
                    msg = json.dumps({"uri": os.path.join(root, d)})
                    rabbit_connection.publish_message(msg, routing_key)

                    dir_count += 1

        elif args.type == "file":
            for file in files:
                # Ignore hidden files
                if re.match(regex, dir) and not os.path.basename(file).startswith("."):
                    # Submit items to rabbit queue for processing during recursion
                    msg = json.dumps({"uri": os.path.join(root, file)})
                    rabbit_connection.publish_message(msg, routing_key)

                    file_count += 1

    logger.info(f"Found and submitted {dir_count} directories and {file_count} files.")


if __name__ == "__main__":
    main()
