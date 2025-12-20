import xml.etree.ElementTree as ET

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from xml.dom import minidom

from ..track import Track
from .writer import Writer
from ...utils.helpers import to_string
from ...utils.logger import logger


namespace_urls = {
    '': "http://www.topografix.com/GPX/1/1",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
    'tpx': "http://www.garmin.com/xmlschemas/TrackPointExtension/v2",
    'adx': "http://www.n3r1.com/xmlschemas/ActivityDataExtensions/v1",
}

namespace_schemas = {
    '': "http://www.topografix.com/GPX/1/1/gpx.xsd",
    'tpx': "http://www.garmin.com/xmlschemas/TrackPointExtensionv2.xsd",
    'adx': "http://www.n3r1.com/xmlschemas/ActivityDataExtensionsv1.xsd",
}

tag = SimpleNamespace(
    gpx="{" + namespace_urls[''] + "}",
    tpx="{" + namespace_urls['tpx'] + "}",
    adx="{" + namespace_urls['adx'] + "}",
)


class GpxWriter(Writer):
    def write(self, track: Track, path: Path) -> bool:
        logger.debug(f"Writing GPX file to '{path}'...")

        self._register_namespaces()
        gpx = self._create_gpx_element()
        metadata = self._create_metadata_element(gpx, track)
        #future: wpt
        #future: rte
        trk = self._create_trk_element(gpx, track)
        trk_ext = self._create_trk_extensions(trk, track)
        trkseg = self._create_trkseg_element(trk, track)
        trkpts = self._create_trkpt_elements(trkseg, track)

        return self._write_file(gpx, path)


    def _register_namespaces(self) -> None:
        for key, url in namespace_urls.items():
            ET.register_namespace(key, url)


    def _create_gpx_element(self) -> ET.Element:
        gpx = ET.Element(f"{tag.gpx}gpx", {
            'version': "1.1",
            'creator': "fitt",
            f"{tag.gpx}schemaLocation": " ".join([f"{namespace_urls[key]} {namespace_schemas[key]}" for key in namespace_schemas.keys()])
        })
        return gpx
    

    def _create_metadata_element(self, gpx: ET.Element, track: Track) -> ET.Element:
        metadata = ET.SubElement(gpx, f"{tag.gpx}metadata")
        ET.SubElement(metadata, f"{tag.gpx}link", {'href': "https://github.com/neri14/fitt"})

        if 'start_time' in track.metadata:
            ET.SubElement(metadata, f"{tag.gpx}time").text = to_string(track.metadata['start_time'])
        if all(k in track.metadata for k in ('minlat', 'minlon', 'maxlat', 'maxlon')):
            ET.SubElement(metadata, f"{tag.gpx}bounds", {
                'minlat': str(track.metadata['minlat']),
                'minlon':  str(track.metadata['minlon']),
                'maxlat': str(track.metadata['maxlat']),
                'maxlon': str(track.metadata['maxlon']),
            })
        return metadata


    def _create_trk_element(self, gpx: ET.Element, track: Track) -> ET.Element:
        trk = ET.SubElement(gpx, f"{tag.gpx}trk")
        ET.SubElement(trk, f"{tag.gpx}name").text = str(track.metadata['name']) if 'name' in track.metadata else "Unnamed Activity"

        if 'device' in track.metadata:
            ET.SubElement(trk, f"{tag.gpx}src").text = str(track.metadata['device'])

        track_type = track.metadata['sport'] if 'sport' in track.metadata else "other"
        if 'sub_sport' in track.metadata:
            track_type = f"{track.metadata['sub_sport']}_{track_type}"
        ET.SubElement(trk, f"{tag.gpx}type").text = str(track_type)

        return trk


    def _create_trk_extensions(self, trk: ET.Element, track: Track) -> ET.Element:
        trk_ext = ET.SubElement(trk, f"{tag.gpx}extensions")
        trk_adx = ET.SubElement(trk_ext, f"{tag.adx}ActivityTrackExtension")
        
        if 'total_elapsed_time' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}elapsedtime").text = str(track.metadata['total_elapsed_time'])
        if 'total_timer_time' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}timertime").text = str(track.metadata['total_timer_time'])
        if 'total_distance' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}distance").text = str(track.metadata['total_distance'])
        elif 'total_track_distance' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}distance").text = str(track.metadata['total_track_distance'])
        if 'total_ascent' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}ascent").text = str(track.metadata['total_ascent'])
        if 'total_descent' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}descent").text = str(track.metadata['total_descent'])
        if 'max_grade' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxgrade").text = str(track.metadata['max_grade'])
        if 'min_grade' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}mingrade").text = str(track.metadata['min_grade'])
        if 'total_cycles' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}cycles").text = str(track.metadata['total_cycles'])
        if 'total_strokes' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}strokes").text = str(track.metadata['total_strokes'])
        if 'total_work' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}work").text = str(track.metadata['total_work'])
        if 'total_calories' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}kcal").text = str(track.metadata['total_calories'])

        if 'total_grit' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}grit").text = str(track.metadata['total_grit'])
        if 'avg_flow' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}flow").text = str(track.metadata['avg_flow'])
        
        if 'avg_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgspeed").text = str(track.metadata['avg_speed'])
        elif 'avg_track_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgspeed").text = str(track.metadata['avg_track_speed'])
        if 'max_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxspeed").text = str(track.metadata['max_speed'])
        elif 'max_track_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxspeed").text = str(track.metadata['max_track_speed'])
        
        if 'avg_power' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgpower").text = str(track.metadata['avg_power'])
        if 'max_power' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxpower").text = str(track.metadata['max_power'])
        if 'normalized_power' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}normpower").text = str(track.metadata['normalized_power'])

        if 'avg_vam' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgvam").text = str(track.metadata['avg_vam'])

        if 'avg_respiration_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgrr").text = str(track.metadata['avg_respiration_rate'])
        if 'max_respiration_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxrr").text = str(track.metadata['max_respiration_rate'])
        if 'min_respiration_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}minrr").text = str(track.metadata['min_respiration_rate'])
        
        if 'jump_count' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}jumps").text = str(track.metadata['jump_count'])

        if 'avg_heart_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avghr").text = str(track.metadata['avg_heart_rate'])
        if 'max_heart_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxhr").text = str(track.metadata['max_heart_rate'])

        if 'avg_cadence' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgcad").text = str(track.metadata['avg_cadence'])
        if 'max_cadence' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxcad").text = str(track.metadata['max_cadence'])

        if 'avg_temperature' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgatemp").text = str(track.metadata['avg_temperature'])
        if 'max_temperature' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxatemp").text = str(track.metadata['max_temperature'])
        if 'min_temperature' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}minatemp").text = str(track.metadata['min_temperature'])

        return trk_ext


    def _create_trkseg_element(self, trk: ET.Element, track: Track) -> ET.Element:
        trkseg = ET.SubElement(trk, f"{tag.gpx}trkseg")
        return trkseg


    def _create_trkpt_elements(self, trkseg: ET.Element, track: Track) -> list[ET.Element]:
        trkpts = []
        for timestamp, data in track.points_iter:
            trkpt = self._create_trkpt_element(trkseg, timestamp, data)
            if trkpt:
                trkpts.append(trkpt)
        logger.debug(f"Created {len(trkpts)} track points in GPX.")
        return trkpts


    def _create_trkpt_element(self, trkseg: ET.Element, timestamp: datetime, data: dict) -> ET.Element | None:
        if 'latitude' not in data or 'longitude' not in data:
            logger.warning("Skipping record without position when generating gpx file")
            return None

        trkpt = ET.SubElement(trkseg, f"{tag.gpx}trkpt",
                              lat=str(data['latitude']),
                              lon=str(data['longitude']))
        
        if 'elevation' in data:
            ET.SubElement(trkpt, f"{tag.gpx}ele").text = str(data['elevation'])

        ET.SubElement(trkpt, f"{tag.gpx}time").text = to_string(timestamp)

        trkpt_ext = ET.SubElement(trkpt, f"{tag.gpx}extensions")

        trkpt_tpx = ET.SubElement(trkpt_ext, f"{tag.tpx}TrackPointExtension")

        if 'temperature' in data:
            ET.SubElement(trkpt_tpx, f"{tag.tpx}atemp").text = str(data['temperature'])
        if 'heart_rate' in data:
            ET.SubElement(trkpt_tpx, f"{tag.tpx}hr").text = str(data['heart_rate'])
        if 'cadence' in data:
            ET.SubElement(trkpt_tpx, f"{tag.tpx}cad").text = str(data['cadence'])
        if 'speed' in data:
            ET.SubElement(trkpt_tpx, f"{tag.tpx}speed").text = str(data['speed'])

        trkpt_adx = ET.SubElement(trkpt_ext, f"{tag.adx}ActivityTrackPointExtension")

        if 'time' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}time").text = str(data['time'])
        if 'smooth_elevation' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}smoothele").text = str(data['smooth_elevation'])
        if 'distance' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}dist").text = str(data['distance'])
        if 'calories' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}kcal").text = str(data['calories'])

        if 'respiration_rate' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rr").text = str(data['respiration_rate'])
        if 'core_temperature' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}ctemp").text = str(data['core_temperature'])

        if 'power' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power").text = str(data['power'])
        if 'power3s' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power3s").text = str(data['power3s'])
        if 'power10s' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power10s").text = str(data['power10s'])
        if 'power30s' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power30s").text = str(data['power30s'])
        if 'accumulated_power' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}accpower").text = str(data['accumulated_power'])

        if 'grade' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}grade").text = str(data['grade'])
        if 'vertical_speed' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}vspeed").text = str(data['vertical_speed'])

        if 'left_torque_effectiveness' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}ltrqeff").text = str(data['left_torque_effectiveness'])
        if 'right_torque_effectiveness' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rtrqeff").text = str(data['right_torque_effectiveness'])
        if 'left_pedal_smoothness' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}lpdlsmooth").text = str(data['left_pedal_smoothness'])
        if 'right_pedal_smoothness' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rpdlsmooth").text = str(data['right_pedal_smoothness'])
        if 'combined_pedal_smoothness' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}cpdlsmooth").text = str(data['combined_pedal_smoothness'])

        if 'grit' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}grit").text = str(data['grit'])
        if 'flow' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}flow").text = str(data['flow'])

        if 'active_climb' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}climb").text = str(data['active_climb'])

        if 'front_gear_num' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}fgearnum").text = str(data['front_gear_num'])
        if 'front_gear' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}fgear").text = str(data['front_gear'])
        if 'rear_gear_num' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rgearnum").text = str(data['rear_gear_num'])
        if 'rear_gear' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rgear").text = str(data['rear_gear'])

        if 'jump_distance' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumpdist").text = str(data['jump_distance'])
        if 'jump_height' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumpheight").text = str(data['jump_height'])
        if 'jump_hang_time' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumptime").text = str(data['jump_hang_time'])
        if 'jump_score' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumpscore").text = str(data['jump_score'])

        return trkpt


    def _write_file(self, gpx: ET.Element, path: Path) -> bool:
        try:
            rough = ET.tostring(gpx, 'utf-8')
            pretty = minidom.parseString(rough).toprettyxml(indent="  ")
            with open(path, "w", encoding="utf-8") as f:
                f.write(pretty)
        except Exception as e:
            logger.error(f"Error writing GPX file to '{path}': {e}")
            return False

        return True

