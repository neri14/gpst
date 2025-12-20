# GPS Tools

[![CI](https://github.com/neri14/gpst/actions/workflows/ci.yml/badge.svg?branch=master)](https://github.com/neri14/gpst/actions/workflows/ci.yml)
[![Coverage Status](https://codecov.io/gh/neri14/gpst/branch/master/graph/badge.svg)](https://codecov.io/gh/neri14/gpst)
[![PyPI - Version](https://img.shields.io/pypi/v/gpst)](https://pypi.org/project/gpst/)

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

**GPS Tools** - A collection of tools to work with GPS track files.


## Note

GPX input not yet supported.


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
    plot      Plot data from the fit file.
    process   Process GPS track file and write results to a GPX file.

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
```


### gpst process

```
$ gpst process -h
usage: gpst process [-h] -o OUT_FILE [-y] IN_FILE

positional arguments:
  IN_FILE               Path to input file (.gpx or .fit).

options:
  -h, --help            show this help message and exit
  -o, --output OUT_FILE
                        Path to the output file.
  -y, --yes             Accept questions (e.g. overwrite existing output file).
```


### gpst plot

```
$ gpst plot -h
usage: gpst plot [-h] -x X_AXIS -y Y_AXIS [Y_AXIS ...] [--y-right Y_AXIS_RIGHT [Y_AXIS_RIGHT ...]] [-t {line,scatter}] [--type-right {line,scatter}] [-o OUTPUT] FILE

positional arguments:
  FILE                  Path to input file (.gpx or .fit).

options:
  -h, --help            show this help message and exit
  -x, --x-axis X_AXIS   Field to use for the x-axis.
  -y, --y-axis Y_AXIS [Y_AXIS ...]
                        Field to use for the y-axis.
  --y-right Y_AXIS_RIGHT [Y_AXIS_RIGHT ...]
                        Field to use for the y-axis on the right side.
  -t, --type {line,scatter}
                        Plot type: line, scatter. Default is line.
  --type-right {line,scatter}
                        Plot type for right y-axis: line, scatter. Default is line.
  -o, --output OUTPUT   Path to the output image file. If not provided, shows the plot interactively
```
