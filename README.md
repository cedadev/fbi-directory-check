# FBI Directory Scanner

This code connects to a local disk based queue and is used to submit directories to be checked against the
elasticsearch index.

Differences are then submitted to the rabbit queues to be picked up by the indexing code 

# Installing

1. Install the package `pip install git+https://github.com/cedadev/fbi-directory-check`

# Setup

This code base requires a config file to setup the local queue. This is found in rabbit_indexer/conf

# Running

```
Submit directories to be checked for consistency with the elasticsearch indices.

Usage:

    fbi_directory_check [-r] <dir>

Args:
    dir     Directory to submit

Options: 
    -r      Recursive. Include specified directory and any directories under this point.
            Will not follow symlinks.
```


# Configuration

Config options

| Option             | Description |
| ------------------ | - |
| queue-location     | Directory path to queue databases|
