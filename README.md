# GPS Tools

[![CI](https://github.com/neri14/gpst/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/neri14/gpst/actions/workflows/ci.yml)
[![Coverage Status](https://codecov.io/gh/neri14/gpst/branch/master/graph/badge.svg)](https://codecov.io/gh/neri14/gpst)
[![PyPI - Version](https://img.shields.io/pypi/v/gpst)](https://pypi.org/project/gpst/)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

**GPS Tools** - A collection of tools to work with GPS track files.


## Example Usage

**convert .fit file to .gpx file**

```gpst process track.fit -o track.gpx```


## Detailed Usage

```
$ gpst -h
usage: gpst [-h] [--version] tool ...

GPS Tools - A collection of tools to work with GPS track files.

positional arguments:
  tool        Available tools:
    process   Process GPS track file and write results to a GPX file.

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
```


### gpst process

```
$ gpst process -h
usage: gpst process [-h] -o OUT_FILE IN_FILE

positional arguments:
  IN_FILE               Path to input file (.gpx or .fit).

options:
  -h, --help            show this help message and exit
  -o, --output OUT_FILE
                        Path to the output file.
```