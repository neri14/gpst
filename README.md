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
    map       Draw map of input file.
    plot      Plot data from the fit file.
    process   Process GPS track file and write results to a GPX file.

options:
  -h, --help  show this help message and exit
  --version   show program's version number and exit
```


### gpst process

```
$ gpst process -h
usage: gpst process [-h] -o OUT_FILE [-y] [--fix-elevation DEM_FILE [DEM_FILE ...]] [--dem-crs DEM_CRS] [--elevation-smoothing-window METERS] [--grade-calculation-window METERS] IN_FILE

positional arguments:
  IN_FILE               Path to input file (.gpx or .fit).

options:
  -h, --help            show this help message and exit
  -o, --output OUT_FILE
                        Path to the output file.
  -y, --yes             Accept questions (e.g. overwrite existing output file).
  --fix-elevation DEM_FILE [DEM_FILE ...]
                        Correct elevation data using DEM files.
  --dem-crs DEM_CRS     Coordinate reference system of the DEM files to be used if no CRS is specified in the files themselves (e.g. 'EPSG:4326').
  --elevation-smoothing-window METERS
                        Smoothing window for elevation data in meters (default: 100).
  --grade-calculation-window METERS
                        Window size for grade calculation in meters (default: 100).
```

Example DEM coordinate reference systems:
- PL-KRON86-NH -> 'EPSG:2180'
- PL-EVRF2007-NH -> 'EPSG:9651'


When `--fix-elevation` is in use, tool produces report in form of csv file and png plot, e.g.:

`$ gpst process track.fit -o ./track.gpx -y --fix-elevation ./dem/*.asc --dem-crs EPSG:2180`

[![Elevation Fix](./docs/images/elevation_fix_report.png)](./docs/images/elevation_fix_report.png)

<details>
<summary>Elevation Plot without and with --fix-elevation</summary>

**No fix**

[![Plot](./docs/images/plot_nofix.png)](./docs/images/plot_nofix.png)

**With fix**

[![Plot](./docs/images/plot.png)](./docs/images/plot.png)

</details>


### gpst plot

**Note:** plot tool does not calculate additional fields, to use calculated fields with FIT file, convert with process tool to GPX first

```
$ gpst plot -h
usage: gpst plot [-h] -x X_AXIS -y Y_AXIS [Y_AXIS ...] [--y-right Y_AXIS_RIGHT [Y_AXIS_RIGHT ...]] [-t {line,scatter}] [--type-right {line,scatter}] [--width WIDTH] [--height HEIGHT] [-o OUTPUT] FILE

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
  --width WIDTH         Width of the output image in pixels (default: 2048).
  --height HEIGHT       Height of the output image in pixels (default: 1024).
  -o, --output OUTPUT   Path to the output image file. If not provided, shows the plot interactively.
```

Example:

`$ gpst plot ./track.gpx --x-axis distance --y-axis grade --y-right elevation smooth_elevation -o plot.png --width 1024 --height 512`

[![Plot](./docs/images/plot.png)](./docs/images/plot.png)

### gpst map

**Note:** map tool does not calculate additional fields, to use calculated fields with FIT file, convert with process tool to GPX first

```
$ gpst map -h
usage: gpst map [-h] [--dem DEM_FILE [DEM_FILE ...]] [--dem-crs DEM_CRS] [--width WIDTH] [--height HEIGHT] [--line-width LINE_WIDTH] [-o OUTPUT] [--show-title] [--trim {tight,box}]
                FILE

positional arguments:
  FILE                  Path to input file (.gpx or .fit).

options:
  -h, --help            show this help message and exit
  --dem DEM_FILE [DEM_FILE ...]
                        DEM files to use as background elevation data.
  --dem-crs DEM_CRS     Coordinate reference system of the DEM files to be used if no CRS is specified in the files themselves (e.g. 'EPSG:4326').
  --width WIDTH         Width of the output image in pixels (default: 4096).
  --height HEIGHT       Height of the output image in pixels (default: 4096).
  --line-width LINE_WIDTH
                        Width of the track line (default: 2.5).
  -o, --output OUTPUT   Path to the output image file. If not provided, shows the map interactively.
  --show-title          Show the activity name as the title of the map.
  --trim {tight,box}    Trim the map to the track bounds.
```

Example:

`$ gpst map ./track.gpx --dem ./dem/*.asc --dem-crs EPSG:2180 -o map.png --width 1024 --height 1024 --trim box --line-width 1`

[![Map](./docs/images/map.png)](./docs/images/map.png)


## Limitations

- GPX rte and wpt (and FIT equivalents) are ignored
- track and segment split in GPX (and FIT equivalents) are ignored
- GPX 1.0 is not supported (yet)
- unsupported fields are not preserved (see [list of supported Fields](./FIELDS.md))

- following GPX extensions are utilized for working with GPX files:
  - http://www.garmin.com/xmlschemas/TrackPointExtension/v1
  - http://www.garmin.com/xmlschemas/TrackPointExtension/v2
  - http://www.garmin.com/xmlschemas/GpxExtensions/v2
  - http://www.garmin.com/xmlschemas/GpxExtensions/v3
  - http://www.n3r1.com/xmlschemas/ActivityDataExtensions/v1
