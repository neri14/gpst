# Target


Target tools structure below


## process

Process the FIT/GPX file

`gpst process track.fit --calculate all --fix-altitude asc/*.asc -o track_final.gpx`

Usage:

```
gpst process INPUT_FILE [OPTIONS], where OPTIONS can be:
  --calculate FIELD1 FIELD2 ...          # calculate additional fields (all for all additional fields)
  --fix-altitude DEM_FILE DEM_FILE ...   # correct elevation data using DEM files
  --trim START_TIME END_TIME            # trim track to specified time range
  --add-metadata KEY1=VALUE1 KEY2=VALUE2 ...  # add metadata to the track
  --remove-metadata KEY1 KEY2 ...          # remove specified metadata from the track
  -o OUTPUT_FILE                         # output file (always GPX)
```

Note: if --fix-altitude is used without --calculate, preexisting fields that depend on elevation will be recalculated
  (e.g. grade, total ascent, total descent, smooth_elevation etc.)

Note: fields that can't be calculated because of missing data will be skipped (e.g. if file has no power data, power averages won't be calculated)


## plot

Create a plot from a FIT/GPX file

`gpst plot track.fit --x-axis distance --y-axis elevation --y-right grade -o diagram.png`

Usage:

```
gpst plot INPUT_FILE [OPTIONS], where OPTIONS can be:
  --x-axis FIELD                                # field for x-axis (mandatory)
  --y-axis FIELD1[STYLE1] FIELD2[STYLE2] ...    # fields and optional styles for left y-axis (mandatory), if no style is given, default 'line' is used
  --y-right FIELD1[STYLE1] FIELD2[STYLE2] ...   # fields and optional styles for right y-axis (optional), if no style is given, default 'line' is used
  -o OUTPUT_FILE                                # output image file (optional, if not given, plot is shown on screen)
```

Note: if configured fields are not present in file - they will not be calculated


## map

Create a map from a FIT/GPX file

`gpst map track.gpx --dem asc/*.asc --color grade -o track_map.png`

Usage:

```
gpst map INPUT_FILE [OPTIONS], where OPTIONS can be:
  --dem DEM_FILE DEM_FILE ...    # DEM files for background shaded relief (optional)
  --color FIELD                  # field to color the track by (optional)
  -o OUTPUT_FILE                 # output image file (optional, if not given, map is shown on screen)
```

Note: if field configured for color is not present in file it will not be calculated


## summary

Summarize a FIT/GPX file and print summary statistics

`gpst summary track.fit --fields all --metadata`

Usage:

```
gpst summary INPUT_FILE [OPTIONS], where OPTIONS can be:
  --fields FIELD1 FIELD2 ...    # fields to include in the summary (all for all fields) - min, max, average, total, etc.
  --metadata                    # include metadata in the analysis - e.g. start time, total duration, etc.
```

Note: if configured fields are not present in file - they will not be calculated


## export

Export data from a FIT/GPX file to CSV

`gpst export track.fit --fields all -o track_data.csv`

Usage:

```
gpst export INPUT_FILE [OPTIONS], where OPTIONS can be:
  --fields FIELD1 FIELD2 ...    # fields to include in the export (all for all fields)
  -o OUTPUT_FILE                 # output CSV file
```

Note: if configured fields are not present in file - they will not be calculated
