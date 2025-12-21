import re
import xml.etree.ElementTree as ET

from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from ..track import Track, Value
from .reader import Reader
from ...utils.logger import logger
from ...utils.helpers import timestamp_from_str


class Parser(ABC):
    @abstractmethod
    def parse_metadata(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        raise NotImplementedError("Subclasses must implement parse_metadata method")
    
    @abstractmethod
    def parse_field(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        raise NotImplementedError("Subclasses must implement parse_field method")


class DuymmyParser(Parser):
    def parse_metadata(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        logger.warning(f"Using DuymmyParser for tag \"{tag}\", all data will be ignored.")
        return {}
    
    def parse_field(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        logger.warning(f"Using DuymmyParser for tag \"{tag}\", all data will be ignored.")
        return {}


class Gpx11Parser(Parser):
    def parse_metadata(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        data: dict[str, Value] = {}
        match tag:
            case "name":
                if text is not None:
                    data["name"] = text

            case "src":
                if text is not None:
                    data["device"] = text

            case "type":
                if text is not None:
                    data["sport"] = text

            case "time":
                ts = timestamp_from_str(text)
                if ts is not None:
                    data["start_time"] = ts
                else:
                    logger.warning(f"Invalid time format: '{text}'")

            case "bounds":
                d: dict[str, Value] = {}
                try:
                    d = {k: float(v) for k, v in attrib.items()}
                except ValueError as e:
                    logger.warning(f"Invalid type(s) for bounds attributes, got: {attrib}, error: {e}")

                if all(key in d for key in ("minlat", "minlon", "maxlat", "maxlon")):
                    data.update(d)
                else:
                    logger.warning(f"Missing one or more bounds attributes, got: {attrib}")

            case _:
                logger.debug(f"Ignored GPX 1.1 metadata tag: \"{tag}\"")

        return data

    def parse_field(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        if text is None:
            logger.warning(f"GPX 1.1 field tag \"{tag}\" has no text.")
            return {}

        try:
            data: dict[str, Value] = {}

            match tag:
                case "ele":
                    data["elevation"] = float(text)
                case "time":
                    ts = timestamp_from_str(text)
                    if ts is not None:
                        data["timestamp"] = ts
                    else:
                        logger.warning(f"Invalid time format: '{text}'")
                case "power":# for handling Strava "power" field without proper namespace
                    data["power"] = float(text)
                case _:
                    logger.debug(f"Ignored GPX 1.1 field tag: \"{tag}\"")

            return data
        except ValueError as e:
            logger.warning(f"Invalid type(s) for GPX 1.1 field tag: \"{tag}\", attribs: {attrib}, text: \"{text}\", error: {e}")
        except Exception as e:
            logger.warning(f"Error parsing GPX 1.1 field tag \"{tag}\": {e}")
        return {}


class TpxV2Parser(Parser):
    def parse_metadata(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        logger.debug(f"Ignored TPX V2 metadata tag: \"{tag}\"")
        return {}


    def parse_field(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        if text is None:
            logger.warning(f"TPX V2 field tag \"{tag}\" has no text.")
            return {}

        try:
            data: dict[str, Value] = {}

            match tag:
                case "atemp":
                    data["temperature"] = float(text)
                case "hr":
                    data["heart_rate"] = float(text)
                case "cad":
                    data["cadence"] = int(text)
                case "speed":
                    data["speed"] = float(text)
                case _:
                    logger.debug(f"Ignored TPX V2 field tag: \"{tag}\"")

            return data
        except ValueError as e:
            logger.warning(f"Invalid type(s) for TPX V2 field tag: \"{tag}\", attribs: {attrib}, text: \"{text}\", error: {e}")
        except Exception as e:
            logger.warning(f"Error parsing TPX V2 field tag \"{tag}\": {e}")
        return {}


class GpxxV3Parser(Parser):
    def parse_metadata(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        logger.debug(f"Ignored GPXX V3 metadata tag: \"{tag}\"")
        return {}


    def parse_field(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        if text is None:
            logger.warning(f"GPXX V3 field tag \"{tag}\" has no text.")
            return {}

        try:
            data: dict[str, Value] = {}

            match tag:
                case "Temperature":
                    data["temperature"] = float(text)
                case _:
                    logger.debug(f"Ignored GPXX V3 field tag: \"{tag}\"")

            return data
        except ValueError as e:
            logger.warning(f"Invalid type(s) for GPXX V3 field tag: \"{tag}\", attribs: {attrib}, text: \"{text}\", error: {e}")
        except Exception as e:
            logger.warning(f"Error parsing GPXX V3 field tag \"{tag}\": {e}")
        return {}


class AdxV1Parser(Parser):
    def parse_metadata(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        if text is None:
            logger.warning(f"ADX V1 metadata tag \"{tag}\" has no text.")
            return {}
        try:
            data: dict[str, Value] = {}

            match tag:
                case "elapsedtime":
                    data["total_elapsed_time"] = float(text)
                case "timertime":
                    data["total_timer_time"] = float(text)
                case "distance":
                    data["total_distance"] = float(text)
                case "ascent":
                    data["total_ascent"] = float(text)
                case "descent":
                    data["total_descent"] = float(text)
                case "maxgrade":
                    data["max_grade"] = float(text)
                case "mingrade":
                    data["min_grade"] = float(text)
                case "cycles":
                    data["total_cycles"] = int(text)
                case "strokes":
                    data["total_strokes"] = int(text)
                case "work":
                    data["total_work"] = int(text)
                case "kcal":
                    data["total_calories"] = float(text)
                case "grit":
                    data["total_grit"] = float(text)
                case "flow":
                    data["avg_flow"] = float(text)
                case "avgspeed":
                    data["avg_speed"] = float(text)
                case "maxspeed":
                    data["max_speed"] = float(text)
                case "avgpower":
                    data["avg_power"] = float(text)
                case "maxpower":
                    data["max_power"] = float(text)
                case "normpower":
                    data["normalized_power"] = float(text)
                case "avgvam":
                    data["avg_vam"] = float(text)
                case "avgrr":
                    data["avg_respiration_rate"] = float(text)
                case "maxrr":
                    data["max_respiration_rate"] = float(text)
                case "minrr":
                    data["min_respiration_rate"] = float(text)
                case "jumps":
                    data["jump_count"] = int(text)
                case "avghr":
                    data["avg_heart_rate"] = float(text)
                case "maxhr":
                    data["max_heart_rate"] = float(text)
                case "avgcad":
                    data["avg_cadence"] = int(text)
                case "maxcad":
                    data["max_cadence"] = int(text)
                case "avgatemp":
                    data["avg_temperature"] = float(text)
                case "maxatemp":
                    data["max_temperature"] = float(text)
                case "minatemp":
                    data["min_temperature"] = float(text)
                case _:
                    logger.debug(f"Ignored ADX V1 metadata tag: \"{tag}\"")

            return data
        except ValueError as e:
            logger.warning(f"Invalid type(s) for ADX V1 metadata tag: \"{tag}\", attribs: {attrib}, text: \"{text}\", error: {e}")
        except Exception as e:
            logger.warning(f"Error parsing ADX V1 metadata tag \"{tag}\": {e}")
        return {}


    def parse_field(self, tag: str, attrib: dict[str, str], text: str|None) -> dict[str, Value]:
        if text is None:
            logger.warning(f"ADX V1 field tag \"{tag}\" has no text.")
            return {}

        try:
            data: dict[str, Value] = {}

            match tag:
                case "time":
                    data["time"] = float(text)
                case  "smoothele":
                    data["smooth_elevation"] = float(text)
                case "dist":
                    data["distance"] = float(text)
                case "kcal":
                    data["calories"] = float(text) 
                case "rr":
                    data["respiration_rate"] = float(text)
                case "ctemp":
                    data["core_temperature"] = float(text)
                case "power":
                    data["power"] = float(text)
                case "power3s":
                    data["power3s"] = float(text)
                case "power10s":
                    data["power10s"] = float(text)
                case "power30s":
                    data["power30s"] = float(text)
                case "accpower":
                    data["accumulated_power"] = float(text)
                case "grade":
                    data["grade"] = float(text)
                case "vspeed":
                    data["vertical_speed"] = float(text)
                case "ltrqeff":
                    data["left_torque_effectiveness"] = float(text)
                case "rtrqeff":
                    data["right_torque_effectiveness"] = float(text)
                case "lpdlsmooth":
                    data["left_pedal_smoothness"] = float(text)
                case "rpdlsmooth":
                    data["right_pedal_smoothness"] = float(text)
                case "cpdlsmooth":
                    data["combined_pedal_smoothness"] = float(text)
                case "grit":
                    data["grit"] = float(text)
                case "flow":
                    data["flow"] = float(text)
                case "climb":
                    data["active_climb"] = int(text)
                case "fgearnum":
                    data["front_gear_num"] = int(text)
                case "fgear":
                    data["front_gear"] = int(text)
                case "rgearnum":
                    data["rear_gear_num"] = int(text)
                case "rgear":
                    data["rear_gear"] = int(text)
                case "jumpdist":
                    data["jump_distance"] = float(text)
                case "jumpheight":
                    data["jump_height"] = float(text)
                case "jumptime":
                    data["jump_hang_time"] = float(text)
                case "jumpscore":
                    data["jump_score"] = float(text)
                case _:
                    logger.debug(f"Ignored ADX V1 field tag: \"{tag}\"")

            return data
        except ValueError as e:
            logger.warning(f"Invalid type(s) for ADX V1 field tag: \"{tag}\", attribs: {attrib}, text: \"{text}\", error: {e}")
        except Exception as e:
            logger.warning(f"Error parsing ADX V1 field tag \"{tag}\": {e}")
        return {}


class Namespace:
    _ignore_prefixes = [
        "http://www.",
        "https://www.",
        "http://",
        "https://",
        "www.",
        "www8.",
    ]

    def __init__(self, name: str, parser: Parser, url: str|None = None, xsd_url: str|None = None):
        self.name: str = name
        self.url: str|None = url
        self.xsd_url: str|None = xsd_url
        self.parser: Parser = parser


    @property
    def url_matcher(self) -> str|None:
        if self.url is None:
            return None

        matcher = self.url.lower()
        if matcher is not None:
            for prefix in self._ignore_prefixes:
                if matcher.startswith(prefix):
                    matcher = matcher.removeprefix(prefix)
        return matcher


    def match(self, url: str|None) -> bool:
        if url is None:
            return self.url is None

        matcher = self.url_matcher
        if matcher is None:
            return False

        url_cmp = url.lower()
        return matcher in url_cmp


_namespace = {
    "gpx11": Namespace("GPX 1.1", Gpx11Parser(),
                       "http://www.topografix.com/GPX/1/1",
                       "http://www.topografix.com/GPX/1/1/gpx.xsd"),

    "tpxv1": Namespace("TrackPointExtension v1", TpxV2Parser(), # same parser as for V2 as we handle only same field
                       "http://www.garmin.com/xmlschemas/TrackPointExtension/v1",
                       "http://www.garmin.com/xmlschemas/TrackPointExtensionv1.xsd"),

    "tpxv2": Namespace("TrackPointExtension v2", TpxV2Parser(),
                       "http://www.garmin.com/xmlschemas/TrackPointExtension/v2",
                       "http://www.garmin.com/xmlschemas/TrackPointExtensionv2.xsd"),

    "gpxxv2": Namespace("GpxExtensions v2", GpxxV3Parser(), # same parser as for V3 as we handle only same field
                        "http://www.garmin.com/xmlschemas/GpxExtensions/v2",
                        "http://www.garmin.com/xmlschemas/GpxExtensionsv2.xsd"),

    "gpxxv3": Namespace("GpxExtensions v3", GpxxV3Parser(),
                        "http://www.garmin.com/xmlschemas/GpxExtensions/v3",
                        "http://www.garmin.com/xmlschemas/GpxExtensionsv3.xsd"),

    "adxv1": Namespace("ActivityDataExtensions v1", AdxV1Parser(),
                       "http://www.n3r1.com/xmlschemas/ActivityDataExtensions/v1",
                       "http://www.n3r1.com/xmlschemas/ActivityDataExtensionsv1.xsd"),
}

namespace = SimpleNamespace(**_namespace)

def get_namespace_by_url(url: str|None) -> Namespace|None:
    for ns in _namespace.values():
        if ns.match(url):
            return ns
    return None


def _parse_tag(tag: str) -> tuple[str|None, str]:
    m = re.match(r'^\{(?P<url>[^}]*)\}(?P<tag>.+)$', tag)
    if m:
        return m.group('url'), m.group('tag')
    return None, tag


class GpxReader(Reader):
    def read(self, path: Path) -> Track|None:
        track = Track()

        try:
            logger.debug(f"Parsing GPX file '{path}'...")
            tree = ET.parse(path)
            root = tree.getroot()

            url, tag = _parse_tag(root.tag)
            if not namespace.gpx11.match(url) or tag != "gpx":
                logger.error(f"File '{path}' is not a GPX 1.1 file (root tag: {{{url}}}{tag} expected: {{{namespace.gpx11.url}}}gpx)")
                return None  # not a GPX 1.1 file

            for child in root:
                url, tag = _parse_tag(child.tag)
                if namespace.gpx11.match(url) and tag == "metadata":
                    self._parse_metadata(child, track)
                elif namespace.gpx11.match(url) and tag == "trk":
                    self._parse_track(child, track)

            return track
        except ET.ParseError as e:
            logger.error(f"Failed to parse GPX file '{path}': {e}")
            return None


    def _parse_metadata(self, element: ET.Element, track: Track):
        logger.debug("Parsing GPX metadata...")

        for child in element:
            url, tag = _parse_tag(child.tag)
            ns = get_namespace_by_url(url)

            if ns is None:
                logger.warning(f"Unsupported metadata tag: \"{child.tag}\"")
                continue

            data = ns.parser.parse_metadata(tag, child.attrib, child.text)
            logger.trace(f"Metadata from tag {{{url}}}{tag}: {data}")
            for key, value in data.items():
                track.set_metadata(key, value)


    def _parse_track(self, element: ET.Element, track: Track):
        logger.debug("Parsing GPX track...")

        for child in element:
            url, tag = _parse_tag(child.tag)
            if namespace.gpx11.match(url) and tag == "trkseg":
                self._parse_track_segment(child, track)
            elif namespace.gpx11.match(url) and tag == "extensions":
                self._parse_track_extensions(child, track)
            else:
                ns = get_namespace_by_url(url)
                if ns is None:
                    logger.warning(f"Unsupported track tag: \"{child.tag}\"")
                    continue
                data = ns.parser.parse_metadata(tag, child.attrib, child.text)
                logger.trace(f"Metadata from tag {{{url}}}{tag}: {data}")
                for key, value in data.items():
                    track.set_metadata(key, value)


    def _parse_track_segment(self, element: ET.Element, track: Track):
        logger.debug("Parsing GPX track segment...")

        for child in element:
            url, tag = _parse_tag(child.tag)
            if namespace.gpx11.match(url) and tag == "trkpt":
                self._parse_track_point(child, track)
            else:
                logger.warning(f"Unsupported track segment tag: \"{child.tag}\"")


    def _parse_track_point(self, element: ET.Element, track: Track):
        logger.trace("Parsing GPX track point...")

        lat = element.get("lat")
        lon = element.get("lon")

        if lat is None or lon is None:
            logger.warning("Track point missing latitude or longitude attributes.")
            return
        
        data: dict[str, Value] = {}
        try:
            data['latitude'] = float(lat)
            data['longitude'] = float(lon)
        except ValueError:
            logger.warning(f"Invalid latitude or longitude values: lat='{lat}', lon='{lon}'")
            return
        
        for child in element:
            url, tag = _parse_tag(child.tag)
            ns = get_namespace_by_url(url)

            if ns is None:
                logger.warning(f"Unsupported track point tag: \"{child.tag}\"")
                continue

            if len(child) == 0:
                field_data = ns.parser.parse_field(tag, child.attrib, child.text)
                logger.trace(f"Field data from tag {{{url}}}{tag}: {field_data}")
                data.update(field_data)
            else:
                d = self._parse_track_point_extensions(child)
                data.update(d)
        
        if "timestamp" not in data or not isinstance(data["timestamp"], datetime):
            logger.warning("Track point missing timestamp field.")
            return
        
        track.upsert_point(data["timestamp"], data)


    def _parse_track_point_extensions(self, element: ET.Element) -> dict[str, Value]:
        logger.trace("Parsing GPX track point extensions...")

        data: dict[str, Value] = {}

        for child in element:
            url, tag = _parse_tag(child.tag)
            ns = get_namespace_by_url(url)

            if ns is None:
                logger.warning(f"Unsupported track point extension tag: \"{child.tag}\"")
                continue

            if len(child) == 0:
                field_data = ns.parser.parse_field(tag, child.attrib, child.text)
                logger.trace(f"Field data from tag {{{url}}}{tag}: {field_data}")
                data.update(field_data)
            else:
                d = self._parse_track_point_extensions(child)
                data.update(d)

        return data


    def _parse_track_extensions(self, element: ET.Element, track: Track):
        logger.debug("Parsing GPX track extensions...")

        for child in element:
            url, tag = _parse_tag(child.tag)
            ns = get_namespace_by_url(url)

            if ns is None:
                logger.warning(f"Unsupported track extension tag: \"{child.tag}\"")
                continue

            if len(child) == 0:
                data = ns.parser.parse_metadata(tag, child.attrib, child.text)
                logger.trace(f"Metadata from tag {{{url}}}{tag}: {data}")
                for key, value in data.items():
                    track.set_metadata(key, value)
            else:
                self._parse_track_extensions(child, track)

















        # def walk(element: ET.Element, lvl=0):
        #     print(f"{'  ' * lvl}<{element.tag}>  {element.attrib}")
        #     n = 0
        #     for child in element:
        #         walk(child, lvl + 1)
        #         n += 1
        #     if not n:
        #         print(f"{'  ' * (lvl + 1)}{element.text}")

        # walk(root)

        # return None
