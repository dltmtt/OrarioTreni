import csv
from datetime import date, datetime
from pathlib import Path

from .models import StopType


def to_datetime(timestamp_ms: int | None) -> datetime | None:
    return datetime.fromtimestamp(timestamp_ms / 1000) if timestamp_ms else None


def to_date(timestamp_ms: int | None) -> date | None:
    return datetime.fromtimestamp(timestamp_ms / 1000).date() if timestamp_ms else None


def map_stop_type(stop_type: str) -> str:
    return {
        "P": StopType.DEPARTURE,
        "F": StopType.INTERMEDIATE,
        "A": StopType.ARRIVAL,
    }[stop_type]


def normalize(s: str) -> str:
    return s.strip().replace("  ", " ")


def load_stations_csv() -> list[dict]:
    with Path.open("stations.csv", newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)