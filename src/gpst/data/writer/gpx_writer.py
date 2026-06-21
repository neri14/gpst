import xml.etree.ElementTree as ET

import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
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
    'adx': "http://www.n3r1.com/xmlschemas/ActivityDataExtensions/v11",
    'asx': "http://www.n3r1.com/xmlschemas/ActivitySegmentsExtensions/v11",
    'rtx': "http://www.n3r1.com/xmlschemas/RaceTrackExtensions/v1",
    'gpst': "http://www.n3r1.com/xmlschemas/CustomDataExtensions/v0",
}

namespace_schemas = {
    '': "http://www.topografix.com/GPX/1/1/gpx.xsd",
    'tpx': "http://www.garmin.com/xmlschemas/TrackPointExtensionv2.xsd",
    'adx': "http://www.n3r1.com/xmlschemas/ActivityDataExtensionsv11.xsd",
    'asx': "http://www.n3r1.com/xmlschemas/ActivitySegmentsExtensionsv11.xsd",
    'rtx': "http://www.n3r1.com/xmlschemas/RaceTrackExtensionsv1.xsd",
    'gpst': "http://www.n3r1.com/xmlschemas/CustomDataExtensionsv0.xsd",
}

tag = SimpleNamespace(
    gpx="{" + namespace_urls[''] + "}",
    tpx="{" + namespace_urls['tpx'] + "}",
    adx="{" + namespace_urls['adx'] + "}",
    asx="{" + namespace_urls['asx'] + "}",
    rtx="{" + namespace_urls['rtx'] + "}",
    gpst="{" + namespace_urls['gpst'] + "}"
)


class GpxWriter(Writer):
    def _to_text(self, value: int | float | str | datetime | None) -> str:
        if isinstance(value, float):
            # Keep GPX numeric values in plain decimal form (no scientific notation).
            if math.isnan(value) or math.isinf(value):
                return str(value)

            try:
                text = format(Decimal(str(value)), 'f')
            except (InvalidOperation, ValueError):
                return str(value)

            if '.' in text:
                text = text.rstrip('0').rstrip('.')

            if text in ('', '-0'):
                return '0'

            return text

        return to_string(value)

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
                'minlat': self._to_text(track.metadata['minlat']),
                'minlon':  self._to_text(track.metadata['minlon']),
                'maxlat': self._to_text(track.metadata['maxlat']),
                'maxlon': self._to_text(track.metadata['maxlon']),
            })
        return metadata


    def _create_trk_element(self, gpx: ET.Element, track: Track) -> ET.Element:
        trk = ET.SubElement(gpx, f"{tag.gpx}trk")
        ET.SubElement(trk, f"{tag.gpx}name").text = self._to_text(track.metadata['name']) if 'name' in track.metadata else "Unnamed Activity"

        if 'device' in track.metadata:
            ET.SubElement(trk, f"{tag.gpx}src").text = self._to_text(track.metadata['device'])

        track_type = track.metadata['sport'] if 'sport' in track.metadata else "other"
        if 'sub_sport' in track.metadata:
            track_type = f"{track.metadata['sub_sport']}_{track_type}"
        ET.SubElement(trk, f"{tag.gpx}type").text = self._to_text(track_type)

        return trk


    def _create_trk_extensions(self, trk: ET.Element, track: Track) -> ET.Element:
        trk_ext = ET.SubElement(trk, f"{tag.gpx}extensions")
        trk_adx = self._create_trk_adx_extension(trk_ext, track)

        if len(track.segments) > 0:
            trk_asx = self._create_trk_asx_extension(trk_ext, track)

        return trk_ext
    

    def _create_trk_adx_extension(self, trk_ext: ET.Element, track: Track) -> ET.Element:
        trk_adx = ET.SubElement(trk_ext, f"{tag.adx}ActivityTrackExtension")
 
        if 'total_elapsed_time' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}elapsedtime").text = self._to_text(track.metadata['total_elapsed_time'])
        if 'total_timer_time' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}timertime").text = self._to_text(track.metadata['total_timer_time'])
        if 'total_distance' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}distance").text = self._to_text(track.metadata['total_distance'])
        elif 'total_track_distance' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}distance").text = self._to_text(track.metadata['total_track_distance'])
        if 'total_ascent' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}ascent").text = self._to_text(track.metadata['total_ascent'])
        if 'total_descent' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}descent").text = self._to_text(track.metadata['total_descent'])
        if 'max_grade' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxgrade").text = self._to_text(track.metadata['max_grade'])
        if 'min_grade' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}mingrade").text = self._to_text(track.metadata['min_grade'])
        if 'max_elevation' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxele").text = self._to_text(track.metadata['max_elevation'])
        if 'min_elevation' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}minele").text = self._to_text(track.metadata['min_elevation'])
        if 'total_cycles' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}cycles").text = self._to_text(track.metadata['total_cycles'])
        if 'total_strokes' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}strokes").text = self._to_text(track.metadata['total_strokes'])
        if 'total_work' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}work").text = self._to_text(track.metadata['total_work'])
        if 'total_calories' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}kcal").text = self._to_text(track.metadata['total_calories'])

        if 'total_grit' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}grit").text = self._to_text(track.metadata['total_grit'])
        if 'avg_flow' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}flow").text = self._to_text(track.metadata['avg_flow'])
        
        if 'avg_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgspeed").text = self._to_text(track.metadata['avg_speed'])
        elif 'avg_track_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgspeed").text = self._to_text(track.metadata['avg_track_speed'])
        if 'max_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxspeed").text = self._to_text(track.metadata['max_speed'])
        elif 'max_track_speed' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxspeed").text = self._to_text(track.metadata['max_track_speed'])
        
        if 'avg_power' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgpower").text = self._to_text(track.metadata['avg_power'])
        if 'max_power' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxpower").text = self._to_text(track.metadata['max_power'])
        if 'normalized_power' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}normpower").text = self._to_text(track.metadata['normalized_power'])

        if 'avg_vam' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgvam").text = self._to_text(track.metadata['avg_vam'])

        if 'avg_respiration_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgrr").text = self._to_text(track.metadata['avg_respiration_rate'])
        if 'max_respiration_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxrr").text = self._to_text(track.metadata['max_respiration_rate'])
        if 'min_respiration_rate' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}minrr").text = self._to_text(track.metadata['min_respiration_rate'])
        
        if 'jumps' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}jumps").text = self._to_text(track.metadata['jumps'])

        if 'avg_heart_rate' in track.metadata:
            val = track.metadata['avg_heart_rate']
            if isinstance(val, float):
                val = round(val)
            ET.SubElement(trk_adx, f"{tag.adx}avghr").text = self._to_text(val)
        if 'max_heart_rate' in track.metadata:
            val = track.metadata['max_heart_rate']
            if isinstance(val, float):
                val = round(val)
            ET.SubElement(trk_adx, f"{tag.adx}maxhr").text = self._to_text(val)
        if 'avg_cadence' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgcad").text = self._to_text(track.metadata['avg_cadence'])
        if 'max_cadence' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxcad").text = self._to_text(track.metadata['max_cadence'])

        if 'avg_temperature' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}avgatemp").text = self._to_text(track.metadata['avg_temperature'])
        if 'max_temperature' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}maxatemp").text = self._to_text(track.metadata['max_temperature'])
        if 'min_temperature' in track.metadata:
            ET.SubElement(trk_adx, f"{tag.adx}minatemp").text = self._to_text(track.metadata['min_temperature'])

        return trk_adx


    def _create_trk_asx_extension(self, trk_ext: ET.Element, track: Track) -> ET.Element:
        trk_asx = ET.SubElement(trk_ext, f"{tag.asx}ActivitySegmentsExtension")

        for ts, segment in track.segments_iter:
            trk_seg = ET.SubElement(trk_asx, f"{tag.asx}segment")

            if 'name' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}name").text = self._to_text(segment['name'])
            if 'type' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}type").text = self._to_text(segment['type'])
            if 'source' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}source").text = self._to_text(segment['source'])
            
            if 'start_time' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}starttime").text = to_string(segment['start_time'])
            if 'end_time' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}endtime").text = to_string(segment['end_time'])

            if 'start_timer' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}starttimer").text = self._to_text(segment['start_timer'])
            if 'end_timer' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}endtimer").text = self._to_text(segment['end_timer'])

            if 'start_distance' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}startdist").text = self._to_text(segment['start_distance'])
            if 'end_distance' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}enddist").text = self._to_text(segment['end_distance'])

            if 'start_elevation' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}startele").text = self._to_text(segment['start_elevation'])
            if 'end_elevation' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}endele").text = self._to_text(segment['end_elevation'])

            if 'start_ascent' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}startasc").text = self._to_text(segment['start_ascent'])
            if 'end_ascent' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}endasc").text = self._to_text(segment['end_ascent'])
            if 'start_descent' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}startdesc").text = self._to_text(segment['start_descent'])
            if 'end_descent' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}enddesc").text = self._to_text(segment['end_descent'])

            if 'start_latitude' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}startlat").text = self._to_text(segment['start_latitude'])
            if 'start_longitude' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}startlon").text = self._to_text(segment['start_longitude'])
            if 'end_latitude' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}endlat").text = self._to_text(segment['end_latitude'])
            if 'end_longitude' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}endlon").text = self._to_text(segment['end_longitude'])

            if 'minlat' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}minlat").text = self._to_text(segment['minlat'])
            if 'minlon' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}minlon").text = self._to_text(segment['minlon'])
            if 'maxlat' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}maxlat").text = self._to_text(segment['maxlat'])
            if 'maxlon' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}maxlon").text = self._to_text(segment['maxlon'])

            if 'total_elapsed_time' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}elapsedtime").text = self._to_text(segment['total_elapsed_time'])
            if 'total_timer_time' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}timertime").text = self._to_text(segment['total_timer_time'])
            if 'total_distance' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}distance").text = self._to_text(segment['total_distance'])
            if 'total_ascent' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}ascent").text = self._to_text(segment['total_ascent'])
            if 'total_descent' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}descent").text = self._to_text(segment['total_descent'])

            if 'avg_grade' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}avggrade").text = self._to_text(segment['avg_grade'])
            if 'max_grade' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}maxgrade").text = self._to_text(segment['max_grade'])
            if 'min_grade' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}mingrade").text = self._to_text(segment['min_grade'])

            if 'max_elevation' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}maxele").text = self._to_text(segment['max_elevation'])
            if 'min_elevation' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}minele").text = self._to_text(segment['min_elevation'])

            if 'avg_speed' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}avgspeed").text = self._to_text(segment['avg_speed'])
            if 'max_speed' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}maxspeed").text = self._to_text(segment['max_speed'])

            if 'avg_vam' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}avgvam").text = self._to_text(segment['avg_vam'])

            if 'avg_power' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}avgpower").text = self._to_text(segment['avg_power'])
            if 'max_power' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}maxpower").text = self._to_text(segment['max_power'])
            if 'normalized_power' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}normpower").text = self._to_text(segment['normalized_power'])

            if 'avg_heart_rate' in segment:
                val = segment['avg_heart_rate']
                if isinstance(val, float):
                    val = round(val)
                ET.SubElement(trk_seg, f"{tag.asx}avghr").text = self._to_text(val)
            if 'max_heart_rate' in segment:
                val = segment['max_heart_rate']
                if isinstance(val, float):
                    val = round(val)
                ET.SubElement(trk_seg, f"{tag.asx}maxhr").text = self._to_text(val)

            if 'avg_cadence' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}avgcad").text = self._to_text(segment['avg_cadence'])
            if 'max_cadence' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}maxcad").text = self._to_text(segment['max_cadence'])

            if 'total_cycles' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}cycles").text = self._to_text(segment['total_cycles'])
            if 'total_strokes' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}strokes").text = self._to_text(segment['total_strokes'])
            if 'total_work' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}work").text = self._to_text(segment['total_work'])
            if 'total_calories' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}kcal").text = self._to_text(segment['total_calories'])

            if 'total_grit' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}grit").text = self._to_text(segment['total_grit'])
            if 'avg_flow' in segment:
                ET.SubElement(trk_seg, f"{tag.asx}flow").text = self._to_text(segment['avg_flow'])

        return trk_asx


    def _create_trkseg_element(self, trk: ET.Element, track: Track) -> ET.Element:
        trkseg = ET.SubElement(trk, f"{tag.gpx}trkseg")
        return trkseg


    def _create_trkpt_elements(self, trkseg: ET.Element, track: Track) -> list[ET.Element]:
        trkpts = []
        for timestamp, data in track.points_iter:
            trkpt = self._create_trkpt_element(trkseg, timestamp, data, track)
            if trkpt is not None:
                trkpts.append(trkpt)
        logger.debug(f"Created {len(trkpts)} track points in GPX.")
        return trkpts


    def _create_trkpt_element(self, trkseg: ET.Element, timestamp: datetime, data: dict, track: Track) -> ET.Element | None:
        if 'lat' not in data or 'lon' not in data:
            logger.warning("Skipping record without position when generating gpx file")
            return None

        trkpt = ET.SubElement(trkseg, f"{tag.gpx}trkpt",
                              lat=self._to_text(data['lat']),
                              lon=self._to_text(data['lon']))
        
        if 'ele' in data:
            ET.SubElement(trkpt, f"{tag.gpx}ele").text = self._to_text(data['ele'])

        ET.SubElement(trkpt, f"{tag.gpx}time").text = to_string(timestamp)

        trkpt_ext = ET.SubElement(trkpt, f"{tag.gpx}extensions")

        trkpt_tpx = ET.SubElement(trkpt_ext, f"{tag.tpx}TrackPointExtension")

        if 'atemp' in data:
            ET.SubElement(trkpt_tpx, f"{tag.tpx}atemp").text = self._to_text(data['atemp'])
        if 'hr' in data:
            val = data['hr']
            if isinstance(val, float):
                val = round(val)
            ET.SubElement(trkpt_tpx, f"{tag.tpx}hr").text = self._to_text(val)
        if 'cad' in data:
            ET.SubElement(trkpt_tpx, f"{tag.tpx}cad").text = self._to_text(data['cad'])
        if 'speed' in data:
            ET.SubElement(trkpt_tpx, f"{tag.tpx}speed").text = self._to_text(data['speed'])

        trkpt_adx = ET.SubElement(trkpt_ext, f"{tag.adx}ActivityTrackPointExtension")

        if 'timer' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}timer").text = self._to_text(data['timer'])
        if 'smoothele' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}smoothele").text = self._to_text(data['smoothele'])
        if 'dist' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}dist").text = self._to_text(data['dist'])
        if 'kcal' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}kcal").text = self._to_text(data['kcal'])

        if 'rr' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rr").text = self._to_text(data['rr'])
        if 'ctemp' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}ctemp").text = self._to_text(data['ctemp'])

        if 'power' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power").text = self._to_text(data['power'])
        if 'power3s' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power3s").text = self._to_text(data['power3s'])
        if 'power10s' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power10s").text = self._to_text(data['power10s'])
        if 'power30s' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}power30s").text = self._to_text(data['power30s'])
        if 'accpower' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}accpower").text = self._to_text(data['accpower'])

        if 'grade' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}grade").text = self._to_text(data['grade'])
        if 'asc' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}asc").text = self._to_text(data['asc'])
        if 'desc' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}desc").text = self._to_text(data['desc'])
        if 'vspeed' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}vspeed").text = self._to_text(data['vspeed'])

        if 'ltrqeff' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}ltrqeff").text = self._to_text(data['ltrqeff'])
        if 'rtrqeff' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rtrqeff").text = self._to_text(data['rtrqeff'])
        if 'lpdlsmooth' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}lpdlsmooth").text = self._to_text(data['lpdlsmooth'])
        if 'rpdlsmooth' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rpdlsmooth").text = self._to_text(data['rpdlsmooth'])
        if 'cpdlsmooth' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}cpdlsmooth").text = self._to_text(data['cpdlsmooth'])

        if 'grit' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}grit").text = self._to_text(data['grit'])
        if 'flow' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}flow").text = self._to_text(data['flow'])

        if 'climb' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}climb").text = self._to_text(data['climb'])

        if 'fgearnum' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}fgearnum").text = self._to_text(data['fgearnum'])
        if 'fgear' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}fgear").text = self._to_text(data['fgear'])
        if 'rgearnum' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rgearnum").text = self._to_text(data['rgearnum'])
        if 'rgear' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}rgear").text = self._to_text(data['rgear'])

        if 'jumpdist' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumpdist").text = self._to_text(data['jumpdist'])
        if 'jumpheight' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumpheight").text = self._to_text(data['jumpheight'])
        if 'jumptime' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumptime").text = self._to_text(data['jumptime'])
        if 'jumpscore' in data:
            ET.SubElement(trkpt_adx, f"{tag.adx}jumpscore").text = self._to_text(data['jumpscore'])

        if any(k in data for k in ('rtx_lap', 'rtx_state', 'rtx_lap_distance', 'rtx_overall_best_lap_delta', 'rtx_overall_best_lap', 'rtx_best_lap_delta', 'rtx_best_lap')):
            # TODO check by rtx_ prefix?
            trkpt_rtx = ET.SubElement(trkpt_ext, f"{tag.rtx}RaceTrackExtension")

            if 'rtx_lap' in data:
                ET.SubElement(trkpt_rtx, f"{tag.rtx}rtx_lap").text = self._to_text(data['rtx_lap'])
            if 'rtx_state' in data:
                ET.SubElement(trkpt_rtx, f"{tag.rtx}rtx_state").text = self._to_text(data['rtx_state'])
            if 'rtx_lap_distance' in data:
                ET.SubElement(trkpt_rtx, f"{tag.rtx}rtx_lap_distance").text = self._to_text(data['rtx_lap_distance'])
            if 'rtx_overall_best_lap_delta' in data:
                ET.SubElement(trkpt_rtx, f"{tag.rtx}rtx_overall_best_lap_delta").text = self._to_text(data['rtx_overall_best_lap_delta'])
            if 'rtx_overall_best_lap' in data:
                ET.SubElement(trkpt_rtx, f"{tag.rtx}rtx_overall_best_lap").text = self._to_text(data['rtx_overall_best_lap'])
            if 'rtx_best_lap_delta' in data:
                ET.SubElement(trkpt_rtx, f"{tag.rtx}rtx_best_lap_delta").text = self._to_text(data['rtx_best_lap_delta'])
            if 'rtx_best_lap' in data:
                ET.SubElement(trkpt_rtx, f"{tag.rtx}rtx_best_lap").text = self._to_text(data['rtx_best_lap'])

        if len(track.custom_fields):
            trkpt_gpst = ET.SubElement(trkpt_ext, f"{tag.gpst}CustomDataExtension")
            for key in track.custom_fields:
                if key in data:
                    ET.SubElement(trkpt_gpst, f"{tag.gpst}{key}").text = self._to_text(data[key])

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

