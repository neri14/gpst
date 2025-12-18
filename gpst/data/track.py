import logging

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, TypeAlias

from ..utils.helpers import to_string, timestamp_str


Value: TypeAlias = int | float | str | datetime


@dataclass
class Type:
    name: str
    pytype: type | None = None
    unit: str | None = None
    symbol: str | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None


cadence_t           = Type('cadence',          int,          'revolutions per minute',  'rpm',    0,        None)
calories_t          = Type('calories',         float,        'kilocalories',            'kcal',   0,        None)
distance_t          = Type('distance',         float,        'meters',                  'm',      0,        None)
elevation_t         = Type('elevation',        float,        'meters',                  'm',      None,     None)
grade_t             = Type('grade',            float,        'percent',                 '%',      0,        None)
heart_rate_t        = Type('heart rate',       float,          'beats per minute',        'bpm',    0,        None)
latitude_t          = Type('latitude',         float,        'degrees',                 '°',      -90.0,    90.0)
longitude_t         = Type('longitude',        float,        'degrees',                 '°',      -180.0,   180.0)
power_t             = Type('power',            float,        'watts',                   'W',      0,        None)
respiration_rate_t  = Type('respiration rate', float,          'breaths per minute',      'bpm',    0,        None)
speed_t             = Type('speed',            float,        'meters per second',       'm/s',    0,        None)
teeth_t             = Type('teeth',            int,          'number of teeth',         'teeth',  1,        None)
temperature_t       = Type('temperature',      float,        'degrees Celsius',         '°C',     -273.15,  None)
timestamp_t         = Type('timestamp',        datetime,     None,                      None,     None,     None)
time_t              = Type('time',             float,        'seconds',                 's',      0,        None)
work_t              = Type('work',             int,          'joules',                  'J',      0,        None)

int_t               = Type('int',              int,          None,                      None,     None,     None)
float_t             = Type('float',            float,        None,                      None,     None,     None)
percent_t           = Type('percent',          float,        'percent',                 '%',      0,        100)
string_t            = Type('string',           str,          None,                      None,     None,     None)

unknown_t           = Type('unknown',          None,         None,                      None,     None,     None)


point_fields = {
    'time':                             time_t,
    'timestamp':                        timestamp_t,
    'position_lat':                     latitude_t,
    'position_long':                    longitude_t,
    'elevation':                        elevation_t,
    'smooth_elevation':                 elevation_t,
    'heart_rate':                       heart_rate_t,
    'cadence':                          cadence_t,
    'distance':                         distance_t,
    'track_distance':                   distance_t,
    'speed':                            speed_t,
    'track_speed':                      speed_t,
    'power':                            power_t,
    'power3s':                          power_t,
    'power10s':                         power_t,
    'power30s':                         power_t,
    'grade':                            grade_t,
    'temperature':                      temperature_t,
    'accumulated_power':                power_t,
    'gps_accuracy':                     distance_t,
    'vertical_speed':                   speed_t,
    'calories':                         calories_t,
    'left_torque_effectiveness':        percent_t,
    'right_torque_effectiveness':       percent_t,
    'left_pedal_smoothness':            percent_t,
    'right_pedal_smoothness':           percent_t,
    'combined_pedal_smoothness':        percent_t,
    'respiration_rate':                 respiration_rate_t,
    'grit':                             float_t,
    'flow':                             float_t,
    'core_temperature':                 temperature_t,
    'front_gear_num':                   int_t,
    'front_gear':                       teeth_t,
    'rear_gear_num':                    int_t,
    'rear_gear':                        teeth_t,
    'active_climb':                     int_t,
    'jump_distance':                    distance_t,
    'jump_height':                      distance_t,
    'jump_rotations':                   int_t,
    'jump_hang_time':                   time_t,
    'jump_score':                       float_t,
}

metadata_fields = {
    'start_time':                       timestamp_t,
    'end_time':                         timestamp_t,#"timestamp" in fit session msg is not reliable - either calculate or delete
    'start_position_lat':               latitude_t,
    'start_position_long':              longitude_t,
    'end_position_lat':                 latitude_t,
    'end_position_long':                longitude_t,
    'minlat':                           latitude_t,
    'minlon':                           longitude_t,
    'maxlat':                           latitude_t,
    'maxlon':                           longitude_t,
    'total_elapsed_time':               time_t,
    'total_timer_time':                 time_t,
    'total_distance':                   distance_t,
    'total_cycles':                     int_t,
    'total_work':                       work_t,
    'avg_speed':                        speed_t,
    'max_speed':                        speed_t,
    'training_load_peak':               float_t,
    'total_grit':                       float_t,
    'avg_flow':                         float_t,
    'total_calories':                   calories_t,
    'avg_power':                        power_t,
    'max_power':                        power_t,
    'total_ascent':                     elevation_t,
    'total_descent':                    elevation_t,
    'normalized_power':                 power_t,
    'training_stress_score':            float_t,
    'intensity_factor':                 float_t,
    'threshold_power':                  power_t,
    'avg_vam':                          speed_t,
    'avg_respiration_rate':             respiration_rate_t,
    'max_respiration_rate':             respiration_rate_t,
    'min_respiration_rate':             respiration_rate_t,
    'jump_count':                       int_t,
    'avg_right_torque_effectiveness':   percent_t,
    'avg_left_torque_effectiveness':    percent_t,
    'avg_right_pedal_smoothness':       percent_t,
    'avg_left_pedal_smoothness':        percent_t,
    'avg_heart_rate':                   heart_rate_t,
    'max_heart_rate':                   heart_rate_t,
    'avg_cadence':                      cadence_t,
    'max_cadence':                      cadence_t,
    'avg_temperature':                  temperature_t,
    'max_temperature':                  temperature_t,
    'min_temperature':                  temperature_t,
    'total_anaerobic_training_effect':  float_t,
    'total_strokes':                    int_t,
    'sport_profile_name':               string_t,
    'sport':                            string_t,
    'sub_sport':                        string_t,
    'name':                             string_t,
    'device':                           string_t,
}


class Track:
    def __init__(self) -> None:
        self._points: dict[datetime, dict[str, Value]] = {}
        self._metadata: dict[str, Value] = {}


    @property
    def points(self) -> dict[datetime, dict[str, Value]]:
        return self._points


    @property
    def points_iter(self) -> Iterable[tuple[datetime, dict[str, Value]]]:
        for ts in sorted(self._points.keys()):
            yield ts, self._points[ts]


    @property
    def metadata(self) -> dict[str, Value]:
        return self._metadata


    def __repr__(self) -> str:
        data = []
        if 'name' in self._metadata:
            data.append(f"name=\"{self._metadata.get('name')}\"")
        if 'start_time' in self._metadata:
            data.append(f"start_time=\"{to_string(self._metadata.get('start_time'))}\"")
        if 'end_time' in self._metadata:
            data.append(f"end_time=\"{to_string(self._metadata.get('end_time'))}\"")
        data.append(f"num_points={len(self._points)}")

        return f"Track({', '.join(data)})"

    def get_point(self, timestamp: datetime) -> dict[str, Value]:
        return self._points.get(timestamp, {})


    def upsert_point(self, timestamp: datetime, data: dict[str, Value]) -> None:
        for key, value in data.items():
            self._verify_type(key, value, point_fields.get(key), timestamp)

        if timestamp not in self._points:
            self._points[timestamp] = {}
        self._points[timestamp].update(data)


    def set_metadata(self, key: str, value: Value) -> None:
        self._verify_type(key, value, metadata_fields.get(key))
        self._metadata[key] = value


    def _verify_type(self, key: str, value: Value, type_info: Type | None, timestamp: datetime|None = None) -> None:
        tstr = f" at {timestamp_str(timestamp)}" if timestamp else ""

        if not type_info:
            logging.warning(f"Unknown field '{key}'{tstr}.")
            return
        
        if type_info.pytype and type_info.pytype is float and isinstance(value, int):
            value = float(value)
        
        if type_info.pytype and (not isinstance(value, type_info.pytype)):
            logging.warning(f"Incorrect type for '{key}'{tstr}: expected {type_info.pytype}, got {type(value)}.")
            return
        
        if isinstance(value, (int, float)) and type_info.min_value is not None and value < type_info.min_value:
            logging.warning(f"Value for '{key}'{tstr} below minimum: {value} < {type_info.min_value}.")
            return
        
        if isinstance(value, (int, float)) and type_info.max_value is not None and value > type_info.max_value:
            logging.warning(f"Value for '{key}'{tstr} above maximum: {value} > {type_info.max_value}.")
            return
