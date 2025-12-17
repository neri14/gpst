import logging
import math

from garmin_fit_sdk import Decoder, Stream, Profile
from pathlib import Path

from ..track import Track, Value
from .reader import Reader


class FitReader(Reader):
    semicircles_factor = 180.0 / 2**31

    def read(self, path: Path) -> Track|None:
        cache: dict[str, Value] = {}

        def mesg_listener(mesg_num: int, message: dict) -> None:
            if mesg_num == Profile['mesg_num']['SESSION']: # type: ignore
                self._handle_session_message(message, track)
            elif mesg_num == Profile['mesg_num']['SPORT']: # type: ignore
                self._handle_sport_message(message, track)
            elif mesg_num == Profile['mesg_num']['FILE_ID']: # type: ignore
                self._handle_file_id_message(message, track)
            elif mesg_num == Profile['mesg_num']['RECORD']: # type: ignore
                self._handle_record_message(message, cache, track)
            elif mesg_num == Profile['mesg_num']['EVENT']: # type: ignore
                self._handle_event_message(message, cache, track)
            elif mesg_num == Profile['mesg_num']['CLIMB_PRO']: # type: ignore
                self._handle_climb_message(message, cache, track)
            elif mesg_num == Profile['mesg_num']['JUMP']: # type: ignore
                self._handle_jump_message(message, track)
            # TBD messages: segment_lap, hrv, time_in_zone, lap, split, split_summary, timestamp_correlation, device_info, device_aux_battery_info

        track = Track()
        try:
            stream = Stream.from_file(path)
            decoder = Decoder(stream)
            _, errors = decoder.read(mesg_listener=mesg_listener)

            if errors:
                logging.error(f"Errors decoding fit file:")
                for error in errors:
                    logging.error(f" - {error}")
                return None
        except Exception as e:
            logging.error(f"Failed to read fit file: {e}")
            return None
        return track


    def _handle_session_message(self, message: dict, track: Track) -> None:
        if 'start_time' in message:
            track.set_metadata('start_time', message['start_time'])

        if 'start_position_lat' in message:
            track.set_metadata('start_position_lat', message['start_position_lat'] * self.semicircles_factor)
        if 'start_position_long' in message:
            track.set_metadata('start_position_long', message['start_position_long'] * self.semicircles_factor)
        if 'end_position_lat' in message:
            track.set_metadata('end_position_lat', message['end_position_lat'] * self.semicircles_factor)
        if 'end_position_long' in message:
            track.set_metadata('end_position_long', message['end_position_long'] * self.semicircles_factor)

        if 'nec_lat' in message:
            track.set_metadata('maxlat', message['nec_lat'] * self.semicircles_factor)
        if 'nec_long' in message:
            track.set_metadata('maxlon', message['nec_long'] * self.semicircles_factor)
        if 'swc_lat' in message:
            track.set_metadata('minlat', message['swc_lat'] * self.semicircles_factor)
        if 'swc_long' in message:
            track.set_metadata('minlon', message['swc_long'] * self.semicircles_factor)

        if 'total_elapsed_time' in message:
            track.set_metadata('total_elapsed_time', message['total_elapsed_time'])
        if 'total_timer_time' in message:
            track.set_metadata('total_timer_time', message['total_timer_time'])
        if 'total_distance' in message:
            track.set_metadata('total_distance', message['total_distance'])
        if 'total_cycles' in message:
            track.set_metadata('total_cycles', message['total_cycles'])
        if 'total_strokes' in message:
            track.set_metadata('total_strokes', message['total_strokes'])
        if 'total_work' in message:
            track.set_metadata('total_work', message['total_work'])

        if 'enhanced_avg_speed' in message:
            track.set_metadata('avg_speed', message['enhanced_avg_speed'])
        elif 'avg_speed' in message:
            track.set_metadata('avg_speed', message['avg_speed'])
        if 'enhanced_max_speed' in message:
            track.set_metadata('max_speed', message['enhanced_max_speed'])
        elif 'max_speed' in message:
            track.set_metadata('max_speed', message['max_speed'])

        if 'avg_power' in message:
            track.set_metadata('avg_power', message['avg_power'])
        if 'max_power' in message:
            track.set_metadata('max_power', message['max_power'])
        if 'normalized_power' in message:
            track.set_metadata('normalized_power', message['normalized_power'])
        if 'threshold_power' in message:
            track.set_metadata('threshold_power', message['threshold_power'])

        if 'avg_heart_rate' in message:
            track.set_metadata('avg_heart_rate', message['avg_heart_rate'])
        if 'max_heart_rate' in message:
            track.set_metadata('max_heart_rate', message['max_heart_rate'])

        if 'avg_cadence' in message:
            track.set_metadata('avg_cadence', message['avg_cadence'])
        if 'max_cadence' in message:
            track.set_metadata('max_cadence', message['max_cadence'])

        if 'enhanced_avg_respiration_rate' in message:
            track.set_metadata('avg_respiration_rate', message['enhanced_avg_respiration_rate'])
        elif 'avg_respiration_rate' in message:
            track.set_metadata('avg_respiration_rate', message['avg_respiration_rate'])
        if 'enhanced_max_respiration_rate' in message:
            track.set_metadata('max_respiration_rate', message['enhanced_max_respiration_rate'])
        elif 'max_respiration_rate' in message:
            track.set_metadata('max_respiration_rate', message['max_respiration_rate'])
        if 'enhanced_min_respiration_rate' in message:
            track.set_metadata('min_respiration_rate', message['enhanced_min_respiration_rate'])
        elif 'min_respiration_rate' in message:
            track.set_metadata('min_respiration_rate', message['min_respiration_rate'])

        if 'total_ascent' in message:
            track.set_metadata('total_ascent', message['total_ascent'])
        if 'total_descent' in message:
            track.set_metadata('total_descent', message['total_descent'])
        if 'avg_vam' in message:
            track.set_metadata('avg_vam', message['avg_vam'])

        if 'jump_count' in message:
            track.set_metadata('jump_count', message['jump_count'])

        if 'avg_right_torque_effectiveness' in message:
            track.set_metadata('avg_right_torque_effectiveness', message['avg_right_torque_effectiveness'])
        if 'avg_left_torque_effectiveness' in message:
            track.set_metadata('avg_left_torque_effectiveness', message['avg_left_torque_effectiveness'])
        if 'avg_right_pedal_smoothness' in message:
            track.set_metadata('avg_right_pedal_smoothness', message['avg_right_pedal_smoothness'])
        if 'avg_left_pedal_smoothness' in message:
            track.set_metadata('avg_left_pedal_smoothness', message['avg_left_pedal_smoothness'])

        if 'training_load_peak' in message:
            track.set_metadata('training_load_peak', message['training_load_peak'])
        if 'total_grit' in message:
            track.set_metadata('total_grit', message['total_grit'])
        if 'avg_flow' in message:
            track.set_metadata('avg_flow', message['avg_flow'])
        if 'total_calories' in message:
            track.set_metadata('total_calories', message['total_calories'])
        if 'training_stress_score' in message:
            track.set_metadata('training_stress_score', message['training_stress_score'])
        if 'intensity_factor' in message:
            track.set_metadata('intensity_factor', message['intensity_factor'])
        if 'total_anaerobic_training_effect' in message:
            track.set_metadata('total_anaerobic_training_effect', message['total_anaerobic_training_effect'])

        if 'avg_temperature' in message:
            track.set_metadata('avg_temperature', message['avg_temperature'])
        if 'max_temperature' in message:
            track.set_metadata('max_temperature', message['max_temperature'])
        if 'min_temperature' in message:
            track.set_metadata('min_temperature', message['min_temperature'])

        if 'sport_profile_name' in message:
            track.set_metadata('sport_profile_name', message['sport_profile_name'])
        if 'sport' in message:
            track.set_metadata('sport', message['sport'])
        if 'sub_sport' in message:
            track.set_metadata('sub_sport', message['sub_sport'])

        track.set_metadata('name',
            self._generate_activity_name(
                track.metadata.get('sport'),
                track.metadata.get('sub_sport'),
                track.metadata.get('sport_profile_name')
            )
        )


    def _handle_sport_message(self, message: dict, track: Track) -> None:
        if 'name' in message:
            track.set_metadata('sport_profile_name', message['name'])
        if 'sport' in message:
            track.set_metadata('sport', message['sport'])
        if 'sub_sport' in message:
            track.set_metadata('sub_sport', message['sub_sport'])

        track.set_metadata('name',
            self._generate_activity_name(
                track.metadata.get('sport'),
                track.metadata.get('sub_sport'),
                track.metadata.get('sport_profile_name')
            )
        )


    def _handle_file_id_message(self, message: dict, track: Track) -> None:
        manufacturer = None
        product = None
        serial_number = None

        if 'manufacturer' in message:
            manufacturer = str(message['manufacturer'])

        if 'garmin_product' in message:
            product = str(message['garmin_product'])
        elif 'product' in message:
            product = str(message['product'])

        if 'serial_number' in message:
            serial_number = str(message['serial_number'])

        device = ""
        if manufacturer is not None:
            device += manufacturer
        if product is not None:
            if device != "":
                device += " "
            device += product

        device = device.replace('_',' ').title()

        if device == "":
            device = "Unknown Device"

        if serial_number is not None:
            device += f" (S/N: {serial_number})"

        track.set_metadata('device', device)


    def _handle_record_message(self, message: dict, cache: dict[str, Value], track: Track) -> None:
        if 'timestamp' not in message:
            logging.warning("RECORD message without timestamp field.")
            return
        
        timestamp = message['timestamp']
        record_data = {'timestamp': timestamp}
        
        if 'position_lat' in message:
            record_data['position_lat'] = message['position_lat'] * self.semicircles_factor
        if 'position_long' in message:
            record_data['position_long'] = message['position_long'] * self.semicircles_factor

        if 'enhanced_altitude' in message:
            record_data['elevation'] = message['enhanced_altitude']
        elif 'altitude' in message:
            record_data['elevation'] = message['altitude']

        if 'vertical_speed' in message:
            record_data['vertical_speed'] = message['vertical_speed']

        if 'enhanced_speed' in message:
            record_data['speed'] = message['enhanced_speed']
        elif 'speed' in message:
            record_data['speed'] = message['speed']

        if 'distance' in message:
            record_data['distance'] = message['distance']
        if 'heart_rate' in message:
            record_data['heart_rate'] = message['heart_rate']
        if 'cadence' in message:
            record_data['cadence'] = message['cadence']

        if 'enhanced_respiration_rate' in message:
            record_data['respiration_rate'] = message['enhanced_respiration_rate']
        elif 'respiration_rate' in message:
            record_data['respiration_rate'] = message['respiration_rate']

        if 'core_temperature' in message:
            record_data['core_temperature'] = message['core_temperature']

        if 'power' in message:
            record_data['power'] = message['power']
        if 'accumulated_power' in message:
            record_data['accumulated_power'] = message['accumulated_power']

        if 'grade' in message:
            record_data['grade'] = message['grade']
        if 'temperature' in message:
            record_data['temperature'] = message['temperature']

        if 'gps_accuracy' in message:
            record_data['gps_accuracy'] = message['gps_accuracy']
        if 'calories' in message:
            record_data['calories'] = message['calories']

        if 'left_right_balance' in message:
            record_data['left_right_balance'] = message['left_right_balance']
        if 'left_torque_effectiveness' in message:
            record_data['left_torque_effectiveness'] = message['left_torque_effectiveness']
        if 'right_torque_effectiveness' in message:
            record_data['right_torque_effectiveness'] = message['right_torque_effectiveness']
        if 'left_pedal_smoothness' in message:
            record_data['left_pedal_smoothness'] = message['left_pedal_smoothness']
        if 'right_pedal_smoothness' in message:
            record_data['right_pedal_smoothness'] = message['right_pedal_smoothness']
        if 'combined_pedal_smoothness' in message:
            record_data['combined_pedal_smoothness'] = message['combined_pedal_smoothness']

        if 'grit' in message:
            record_data['grit'] = message['grit']
        if 'flow' in message:
            record_data['flow'] = message['flow']

        track.upsert_point(timestamp, record_data)

        cached_data = {}
        point = track.get_point(timestamp)
        for key,value in cache.items():
            if key not in point:
                cached_data[key] = value
        if len(cached_data) > 0:
            track.upsert_point(timestamp, cached_data)


    def _handle_event_message(self, message: dict, cache: dict[str, Value], track: Track) -> None:
        if 'timestamp' not in message:
            logging.warning("EVENT message without timestamp field.")
            return
        if 'event' not in message:
            logging.warning("EVENT message without event field.")
            return
        if 'event_type' not in message:
            logging.warning("EVENT message without event_type field.")
            return

        data = {}
        if message['event'] == 'front_gear_change' and message['event_type'] == 'marker':
            front_gear_num = message.get('front_gear_num', None)
            if isinstance(front_gear_num, int) and 0 < front_gear_num < 255:
                data['front_gear_num'] = front_gear_num

            front_gear = message.get('front_gear', None)
            if isinstance(front_gear, int) and 0 < front_gear < 255:
                data['front_gear'] = front_gear

        if message['event'] == 'rear_gear_change' and message['event_type'] == 'marker':
            rear_gear_num = message.get('rear_gear_num', None)
            if isinstance(rear_gear_num, int) and 0 < rear_gear_num < 255:
                data['rear_gear_num'] = rear_gear_num

            rear_gear = message.get('rear_gear', None)
            if isinstance(rear_gear, int) and 0 < rear_gear < 255:
                data['rear_gear'] = rear_gear

        if len(data) > 0:
            timestamp = message['timestamp']
            track.upsert_point(timestamp, data)
            cache.update(data)


    def _handle_climb_message(self, message: dict, cache: dict[str, Value], track: Track) -> None:
        if 'timestamp' not in message:
            logging.warning("ClimbPro message without timestamp field.")
            return
        if 'climb_pro_event' not in message:
            logging.warning("ClimbPro message without climb_pro_event field.")
            return
        if 'climb_number' not in message:
            logging.warning("ClimbPro message without climb_number field.")
            return

        timestamp = message['timestamp']

        if message['climb_pro_event'] == 'start':
            climb = message['climb_number']

            track.upsert_point(timestamp, {'active_climb': climb})
            cache['active_climb'] = climb
        elif message['climb_pro_event'] == 'complete':
            if 'active_climb' not in cache:
                logging.info("ClimbPro 'complete' event without ClimbPro 'start' event. Setting climb active from start.")
                climb = message['climb_number']

                for t,r in track.points_iter:
                    if t < timestamp:
                        r['active_climb'] = climb

            point = track.get_point(timestamp)
            if 'active_climb' in point:
                del point['active_climb']
            if 'active_climb' in cache:
                del cache['active_climb']


    def _handle_jump_message(self, message: dict, track: Track) -> None:
        if 'timestamp' not in message:
            logging.warning("JUMP message without timestamp field.")
            return

        data = {}

        if 'distance' in message and isinstance(message['distance'], (int, float)) and not math.isnan(message['distance']):
            data['jump_distance'] = message['distance']
        if 'height' in message and isinstance(message['height'], (int, float)) and not math.isnan(message['height']):
            data['jump_height'] = message['height']
        if 'rotations' in message and isinstance(message['rotations'], (int, float)) and not math.isnan(message['rotations']):
            data['jump_rotations'] = message['rotations']
        if 'hang_time' in message and isinstance(message['hang_time'], (int, float)) and not math.isnan(message['hang_time']):
            data['jump_hang_time'] = message['hang_time']
        if 'score' in message and isinstance(message['score'], (int, float)) and not math.isnan(message['score']):
            data['jump_score'] = message['score']

        if len(data) > 0:
            track.upsert_point(message['timestamp'], data)


    def _generate_activity_name(self, sport: str|None, sub_sport: str|None, sport_profile_name: str|None) -> str:
        name = ""

        if sport is None:
            name = "Unknown"
        else:
            name = sport.replace('_',' ').title()

        if sub_sport is not None and sub_sport != 'generic':
            name = f"{sub_sport.replace('_',' ').title()} {name}"

        if sport_profile_name is not None:
            name += f" ({sport_profile_name})"

        return name
