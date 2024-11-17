from datetime import date, datetime


def to_datetime(timestamp_ms: int | None) -> datetime | None:
    return datetime.fromtimestamp(timestamp_ms / 1000) if timestamp_ms else None


def to_date(timestamp_ms: int | None) -> date | None:
    return datetime.fromtimestamp(timestamp_ms / 1000).date() if timestamp_ms else None


def map_stop_type(stop_type: str) -> str:
    return {
        "P": "departure",
        "F": "intermediate",
        "A": "arrival",
    }.get(stop_type, stop_type)


def normalize(s: str) -> str:
    return s.strip().replace("  ", " ")
