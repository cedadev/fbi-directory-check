# encoding: utf-8
""" """
__author__ = "Richard Smith"
__date__ = "08 Oct 2021"
__copyright__ = "Copyright 2018 United Kingdom Research and Innovation"
__license__ = "BSD - see LICENSE file in top-level package directory"
__contact__ = "richard.d.smith@stfc.ac.uk"

import argparse
import json
import os
import re
from configparser import RawConfigParser

from fbi_directory_check.core.rabbit_connection import RabbitMQConnection
from fbi_directory_check.utils import valid_path, walk_storage_links


def get_args():
    default_config = os.path.join(os.path.dirname(__file__), "../conf/stac_updater.ini")
    parser = argparse.ArgumentParser(
        description="Submit paths to be re-scanned for stac."
    )
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

    # Check for tags only flag
    # routing_key = f'deposit.log.{DepositAction.DEPOSIT.value}'
    routing_key = ""

    # Get the full path
    abs_root = os.path.abspath(args.dir)

    # Submit items to rabbit queue for processing
    rabbit_connection = RabbitMQConnection(args.conf)

    conf = RawConfigParser()
    conf.read(args.conf)

    regex = rf"{conf.get("scan", "regex", fallback=".*")}"

    # If -r flag, walk the whole tree, if not walk only the immediate directory
    if args.recursive:
        max_depth = None
    else:
        max_depth = 1

    file_count = 0
    dir_count = 0

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

    print(f"Found and submitted  {dir_count} directories and {file_count} files.")


if __name__ == "__main__":
    main()
