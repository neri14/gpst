# Fields

Note: the file was AI generated, may contain errors, consult `track.py` and `gpx_writer.py` files.

## Metadata

| Name | Type | Unit | Symbol | Min | Max | GPX Representation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| start_time | datetime |   |   |   |   | `metadata/time` |
| end_time | datetime |   |   |   |   |   |
| start_latitude | float | degrees | ° | -90.0 | 90.0 |   |
| start_longitude | float | degrees | ° | -180.0 | 180.0 |   |
| end_latitude | float | degrees | ° | -90.0 | 90.0 |   |
| end_longitude | float | degrees | ° | -180.0 | 180.0 |   |
| minlat | float | degrees | ° | -90.0 | 90.0 | `metadata/bounds@minlat` |
| minlon | float | degrees | ° | -180.0 | 180.0 | `metadata/bounds@minlon` |
| maxlat | float | degrees | ° | -90.0 | 90.0 | `metadata/bounds@maxlat` |
| maxlon | float | degrees | ° | -180.0 | 180.0 | `metadata/bounds@maxlon` |
| total_elapsed_time | float | seconds | s | 0 |   | `trk/extensions/adx:elapsedtime` |
| total_timer_time | float | seconds | s | 0 |   | `trk/extensions/adx:timertime` |
| total_distance | float | meters | m | 0 |   | `trk/extensions/adx:distance` |
| total_track_distance | float | meters | m | 0 |   | `trk/extensions/adx:distance` |
| total_cycles | int |   |   |   |   | `trk/extensions/adx:cycles` |
| total_work | int | joules | J | 0 |   | `trk/extensions/adx:work` |
| avg_speed | float | meters per second | m/s | 0 |   | `trk/extensions/adx:avgspeed` |
| avg_track_speed | float | meters per second | m/s | 0 |   | `trk/extensions/adx:avgspeed` |
| max_speed | float | meters per second | m/s | 0 |   | `trk/extensions/adx:maxspeed` |
| max_track_speed | float | meters per second | m/s | 0 |   | `trk/extensions/adx:maxspeed` |
| training_load_peak | float |   |   |   |   |   |
| total_grit | float |   |   |   |   | `trk/extensions/adx:grit` |
| avg_flow | float |   |   |   |   | `trk/extensions/adx:flow` |
| total_calories | float | kilocalories | kcal | 0 |   | `trk/extensions/adx:kcal` |
| avg_power | float | watts | W | 0 |   | `trk/extensions/adx:avgpower` |
| max_power | float | watts | W | 0 |   | `trk/extensions/adx:maxpower` |
| normalized_power | float | watts | W | 0 |   | `trk/extensions/adx:normpower` |
| total_ascent | float | meters | m |   |   | `trk/extensions/adx:ascent` |
| total_descent | float | meters | m |   |   | `trk/extensions/adx:descent` |
| max_grade | float | percent | % |   |   | `trk/extensions/adx:maxgrade` |
| min_grade | float | percent | % |   |   | `trk/extensions/adx:mingrade` |
| training_stress_score | float |   |   |   |   |   |
| intensity_factor | float |   |   |   |   |   |
| threshold_power | float | watts | W | 0 |   |   |
| avg_vam | float | meters per second | m/s | 0 |   | `trk/extensions/adx:avgvam` |
| avg_respiration_rate | float | breaths per minute | bpm | 0 |   | `trk/extensions/adx:avgrr` |
| max_respiration_rate | float | breaths per minute | bpm | 0 |   | `trk/extensions/adx:maxrr` |
| min_respiration_rate | float | breaths per minute | bpm | 0 |   | `trk/extensions/adx:minrr` |
| jump_count | int |   |   |   |   | `trk/extensions/adx:jumps` |
| avg_right_torque_effectiveness | float | percent | % | 0 | 100 |   |
| avg_left_torque_effectiveness | float | percent | % | 0 | 100 |   |
| avg_right_pedal_smoothness | float | percent | % | 0 | 100 |   |
| avg_left_pedal_smoothness | float | percent | % | 0 | 100 |   |
| avg_heart_rate | float | beats per minute | bpm | 0 |   | `trk/extensions/adx:avghr` |
| max_heart_rate | float | beats per minute | bpm | 0 |   | `trk/extensions/adx:maxhr` |
| avg_cadence | int | revolutions per minute | rpm | 0 |   | `trk/extensions/adx:avgcad` |
| max_cadence | int | revolutions per minute | rpm | 0 |   | `trk/extensions/adx:maxcad` |
| avg_temperature | float | degrees Celsius | °C | -273.15 |   | `trk/extensions/adx:avgatemp` |
| max_temperature | float | degrees Celsius | °C | -273.15 |   | `trk/extensions/adx:maxatemp` |
| min_temperature | float | degrees Celsius | °C | -273.15 |   | `trk/extensions/adx:minatemp` |
| total_anaerobic_training_effect | float |   |   |   |   |   |
| total_strokes | int |   |   |   |   | `trk/extensions/adx:strokes` |
| sport_profile_name | str |   |   |   |   |   |
| sport | str |   |   |   |   | `trk/type` |
| sub_sport | str |   |   |   |   | `trk/type` |
| name | str |   |   |   |   | `trk/name` |
| device | str |   |   |   |   | `trk/src` |

## Track Points

| Name | Type | Unit | Symbol | Min | Max | GPX Representation |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| time | float | seconds | s | 0 |   | `trkpt/extensions/adx:time` |
| timestamp | datetime |   |   |   |   | `trkpt/time` |
| latitude | float | degrees | ° | -90.0 | 90.0 | `trkpt@lat` |
| longitude | float | degrees | ° | -180.0 | 180.0 | `trkpt@lon` |
| elevation | float | meters | m |   |   | `trkpt/ele` |
| smooth_elevation | float | meters | m |   |   | `trkpt/extensions/adx:smoothele` |
| heart_rate | float | beats per minute | bpm | 0 |   | `trkpt/extensions/tpx:hr` |
| cadence | int | revolutions per minute | rpm | 0 |   | `trkpt/extensions/tpx:cad` |
| distance | float | meters | m | 0 |   | `trkpt/extensions/adx:dist` |
| track_distance | float | meters | m | 0 |   |   |
| speed | float | meters per second | m/s | 0 |   | `trkpt/extensions/tpx:speed` |
| track_speed | float | meters per second | m/s | 0 |   |   |
| power | float | watts | W | 0 |   | `trkpt/extensions/adx:power` |
| power3s | float | watts | W | 0 |   | `trkpt/extensions/adx:power3s` |
| power10s | float | watts | W | 0 |   | `trkpt/extensions/adx:power10s` |
| power30s | float | watts | W | 0 |   | `trkpt/extensions/adx:power30s` |
| grade | float | percent | % |   |   | `trkpt/extensions/adx:grade` |
| temperature | float | degrees Celsius | °C | -273.15 |   | `trkpt/extensions/tpx:atemp` |
| accumulated_power | float | watts | W | 0 |   | `trkpt/extensions/adx:accpower` |
| gps_accuracy | float | meters | m | 0 |   |   |
| vertical_speed | float | meters per second | m/s |   |   | `trkpt/extensions/adx:vspeed` |
| calories | float | kilocalories | kcal | 0 |   | `trkpt/extensions/adx:kcal` |
| left_torque_effectiveness | float | percent | % | 0 | 100 | `trkpt/extensions/adx:ltrqeff` |
| right_torque_effectiveness | float | percent | % | 0 | 100 | `trkpt/extensions/adx:rtrqeff` |
| left_pedal_smoothness | float | percent | % | 0 | 100 | `trkpt/extensions/adx:lpdlsmooth` |
| right_pedal_smoothness | float | percent | % | 0 | 100 | `trkpt/extensions/adx:rpdlsmooth` |
| combined_pedal_smoothness | float | percent | % | 0 | 100 | `trkpt/extensions/adx:cpdlsmooth` |
| respiration_rate | float | breaths per minute | bpm | 0 |   | `trkpt/extensions/adx:rr` |
| grit | float |   |   |   |   | `trkpt/extensions/adx:grit` |
| flow | float |   |   |   |   | `trkpt/extensions/adx:flow` |
| core_temperature | float | degrees Celsius | °C | -273.15 |   | `trkpt/extensions/adx:ctemp` |
| front_gear_num | int |   |   |   |   | `trkpt/extensions/adx:fgearnum` |
| front_gear | int | number of teeth | teeth | 1 |   | `trkpt/extensions/adx:fgear` |
| rear_gear_num | int |   |   |   |   | `trkpt/extensions/adx:rgearnum` |
| rear_gear | int | number of teeth | teeth | 1 |   | `trkpt/extensions/adx:rgear` |
| active_climb | int |   |   |   |   | `trkpt/extensions/adx:climb` |
| jump_distance | float | meters | m | 0 |   | `trkpt/extensions/adx:jumpdist` |
| jump_height | float | meters | m | 0 |   | `trkpt/extensions/adx:jumpheight` |
| jump_rotations | int |   |   |   |   |   |
| jump_hang_time | float | seconds | s | 0 |   | `trkpt/extensions/adx:jumptime` |
| jump_score | float |   |   |   |   | `trkpt/extensions/adx:jumpscore` |



