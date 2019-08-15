# FBI Directory Scanner

This code connects to a local disk based queue and is used to submit directories to be checked against the
elasticsearch index.

Differences are then submitted to the rabbit queues to be picked up by the indexing code 

## Installing

1. Install the package `pip install git+https://github.com/cedadev/fbi-directory-check`

## Setup

This code base requires a config file to setup the local queue. This is found in rabbit_indexer/conf


## Configuration

Config options

| Option             | Description |
| ------------------ | - |
| queue-location     | Directory path to queue databases|


## Scripts

### scripts/consistency_checker.py

Takes items off a local queue and checks the elastisearch indices (directories and files) against the
 filesystem. If files/directories need adding, messages are sent to the rabbit
 queue for processing. This is to be run as a process. AKA crawler.

## Command Line Utilities

### fbi_q_check

Display the current number of directories in the user submitted
and bot queues. These are processed to check the difference between 
the index and the archive and then actions are submitted to the rabbit
index.

Usage:
 
```fbi_q_check```

### fbi_rescan_dir

Rescan the given directory. This will overwrite the content in the indices
for this directory

Usage:

```fbi_rescan_dir <dir> [-r] [--no-files] [--no-dirs] [--conf <conf>]```

Options:

| Option | Description |
| ------ | ----------- | 
| -r     | Will search all directories recursively |
| --no-files | Will exclude files from the results and only change directories |
| --no-dirs  | Will exclude directories from the results and only change files |
| --conf | Path to configuration file |

### fbi_directory_check 

Submit directories to be checked for consistency between the archive and the indices.

Usage:

```fbi_directory_check (--dir <dir> | --file <file>) [-r] [--conf <conf>]```

Options: 

| Option | Description |
| ------ | ----------- | 
| -r     | Will search all directories recursively |
| --dir | Will exclude files from the results and only change directories |
| --file  | Will exclude directories from the results and only change files |
| --conf | Path to configuration file |