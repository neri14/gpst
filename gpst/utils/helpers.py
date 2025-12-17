from datetime import datetime, timezone


def timestamp_str(dt: datetime|None) -> str:
    if dt is None or not isinstance(dt, datetime):
        return ""
    if dt.tzinfo is None:
        dt_utc = dt.replace(tzinfo=timezone.utc)
    else:
        dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
