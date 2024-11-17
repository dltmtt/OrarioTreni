from datetime import date, datetime, time

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

description = """
This is a wrapper around the ViaggiaTreno API that provides endpoints to retrieve information about trains and stations.
The ViaggiaTreno API is not officially documented, so the endpoints and their parameters are based on reverse-engineering the [ViaggiaTreno website](http://www.viaggiatreno.it/).
"""
tags_metadata = [
    {
        "name": "stations",
        "description": "Get information about train stations, including departures and arrivals.",
    },
    {
        "name": "trains",
        "description": "Get information about trains, including their progress and stops.",
    },
    {
        "name": "other",
    },
]

app = FastAPI(
    title="ViaggiaTreno API Wrapper",
    description=description,
    summary="An API wrapper for ViaggiaTreno, the official Trenitalia API.",
    version="0.1.0",
    contact={
        "name": "Matteo Delton",
        "email": "deltonmatteo@gmail.com",
    },
    openapi_tags=tags_metadata,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

BASE_URI = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"
MIN_ENEE_CODE = 0
MAX_ENEE_CODE = 99999


class Stats(BaseModel):
    trains_since_midnight: int
    trains_running: int
    last_update: datetime


class BaseStation(BaseModel):
    name: str
    enee_code: int


class Departure(BaseModel):
    category: str
    number: int
    departure_date: date
    origin_enee_code: int
    destination: str
    scheduled_track: str | None
    actual_track: str | None
    departure_time: datetime
    departed_from_origin: bool
    delay: int
    warning: str | None


class Arrival(BaseModel):
    category: str
    number: int
    departure_date: date
    origin_enee_code: int
    origin: str
    scheduled_track: str | None
    actual_track: str | None
    arrival_time: datetime
    departed_from_origin: bool
    delay: int
    warning: str | None


class TrainInfo(BaseModel):
    number: int
    origin_enee_code: int
    departure_date: date
    origin: str


class TrainStop(BaseModel):
    enee_code: int
    name: str
    stop_type: str
    actual_arrival_time: datetime | None
    actual_departure_time: datetime | None
    arrived: bool
    departed: bool
    scheduled_arrival_time: datetime | None
    scheduled_departure_time: datetime | None
    scheduled_arrival_track: str | None
    actual_arrival_track: str | None
    scheduled_departure_track: str | None
    actual_departure_track: str | None


class TrainProgress(BaseModel):
    last_update_time: datetime | None
    last_update_station: str | None
    train_type: str
    category: str
    number: int
    departure_date: date
    origin_enee_code: int
    origin: str
    destination: str
    destination_enee_code: int
    train_number_changes: list[dict]
    departure_time: datetime
    arrival_time: datetime
    departed_from_origin: bool
    delay: int
    warning: str
    delay_reason: str | None
    stops: list[TrainStop]


def get(endpoint: str, *args: str) -> dict | str:
    url = f'{BASE_URI}/{endpoint}/{"/".join(str(arg) for arg in args)}'
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    return r.json() if "json" in r.headers["Content-Type"] else r.text


@app.get(
    "/stations/search/{prefix}",
    response_model=list[BaseStation],
    tags=["stations"],
)
def get_stations_matching_prefix(prefix: str) -> list[BaseStation]:
    """Get a list of stations starting with the given text."""
    r = get("cercaStazione", prefix)

    if not r:
        raise HTTPException(
            status_code=204,
            detail="No stations matching the given prefix could be found",
        )

    return [
        BaseStation(name=s["nomeLungo"], enee_code=to_enee_code(s["id"])) for s in r
    ]


@app.get(
    "/stations/{enee_code}/departures",
    response_model=list[Departure],
    tags=["stations"],
)
def get_departures(
    enee_code: int,
    search_datetime: datetime | None = None,
    limit: int = 10,
) -> list[Departure]:
    """Get the departures from a station at a certain time."""
    if search_datetime is None:
        search_datetime = datetime.now()

    departure_datetime = to_string(search_datetime)
    r = get("partenze", to_station_id(enee_code), departure_datetime)

    return [
        Departure(
            category=d["categoriaDescrizione"].strip(),
            number=int(d["numeroTreno"]),
            departure_date=to_date(d["dataPartenzaTreno"]),
            origin_enee_code=to_enee_code(d["codOrigine"]),
            destination=d["destinazione"],
            scheduled_track=d.get("binarioProgrammatoPartenzaDescrizione"),
            actual_track=d.get("binarioEffettivoPartenzaDescrizione"),
            departure_time=to_datetime(d["orarioPartenza"]),
            departed_from_origin=not d["nonPartito"],
            delay=int(d["ritardo"]),
            warning=d.get("subTitle"),
        )
        for d in r[:limit]
    ]


@app.get(
    "/stations/{enee_code}/arrivals",
    response_model=list[Arrival],
    tags=["stations"],
)
def get_arrivals(
    enee_code: int,
    search_datetime: datetime | None = None,
    limit: int = 10,
) -> list[Arrival]:
    """Get the arrivals to a station at a certain time."""
    if search_datetime is None:
        search_datetime = datetime.now()

    arrival_datetime = to_string(search_datetime)
    r = get("arrivi", to_station_id(enee_code), arrival_datetime)

    return [
        Arrival(
            category=a["categoriaDescrizione"].strip(),
            number=int(a["numeroTreno"]),
            departure_date=to_date(a["dataPartenzaTreno"]),
            origin_enee_code=to_enee_code(a["codOrigine"]),
            origin=a["origine"],
            scheduled_track=a["binarioProgrammatoArrivoDescrizione"],
            actual_track=a["binarioEffettivoArrivoDescrizione"],
            arrival_time=to_datetime(a["orarioArrivo"]),
            departed_from_origin=not a["nonPartito"],
            delay=int(a["ritardo"]),
            warning=a["subTitle"],
        )
        for a in r[:limit]
    ]


@app.get("/trains/{train_number}", response_model=list[TrainInfo], tags=["trains"])
def get_trains_with_number(train_number: int) -> list[TrainInfo]:
    r = get("cercaNumeroTrenoTrenoAutocomplete", train_number)

    if not r:
        raise HTTPException(
            status_code=204,
            detail="No trains with the given number could be found",
        )

    # Example responses (note the different formats, hence the complex parsing):
    # 35299 - MILANO CENTRALE - 16/11/24|35299-S01700-1731711600000
    # 2033 - TORINO PORTA NUOVA|2033-S00219-1731711600000
    return [
        TrainInfo(
            number=int(train_info.split()[0]),
            departure_date=to_date(int(train_info.split("|")[1].split("-")[2])),
            origin_enee_code=to_enee_code(train_info.split("|")[1].split("-")[1]),
            origin=train_info.split("|")[0].split(" - ")[1],
        )
        for train_info in r.splitlines()
    ]


@app.get("/trains", response_model=TrainProgress, tags=["trains"])
def get_train_progress(
    origin_enee_code: int,
    train_number: int,
    departure_date: date,
) -> TrainProgress:
    """Get the progress of a train, including its stops and delays."""
    dep_date_ts: int = to_ms_date_timestamp(departure_date)
    r = get(
        "andamentoTreno",
        to_station_id(origin_enee_code),
        train_number,
        dep_date_ts,
    )

    if not r:
        raise HTTPException(
            status_code=204,
            detail="No train with the given number and departure date could be found",
        )

    return TrainProgress(
        last_update_time=to_datetime(r["oraUltimoRilevamento"]),
        last_update_station=r["stazioneUltimoRilevamento"]
        if r["stazioneUltimoRilevamento"] != "--"
        else None,
        train_type=r["tipoTreno"],
        category=r["categoria"],
        number=int(r["numeroTreno"]),
        departure_date=to_date(r["dataPartenzaTreno"]),
        origin_enee_code=to_enee_code(r["idOrigine"]),
        origin=r["origine"],
        destination=r["destinazione"],
        destination_enee_code=to_enee_code(r["idDestinazione"]),
        train_number_changes=[
            {"new_train_number": int(c["nuovoNumeroTreno"]), "station": c["stazione"]}
            for c in r["cambiNumero"]
        ],
        departure_time=to_datetime(r["orarioPartenza"]),
        arrival_time=to_datetime(r["orarioArrivo"]),
        departed_from_origin=not r["nonPartito"],
        delay=int(r["ritardo"] or 0),
        warning=r["subTitle"],
        delay_reason=r["motivoRitardoPrevalente"],
        stops=[
            {
                "enee_code": to_enee_code(s["id"]),
                "name": s["stazione"],
                "stop_type": map_stop_type(s["tipoFermata"]),
                "actual_arrival_time": to_datetime(s["arrivoReale"]),
                "actual_departure_time": to_datetime(s["partenzaReale"]),
                "arrived": to_datetime(s["arrivoReale"]) is not None,
                "departed": to_datetime(s["partenzaReale"]) is not None,
                "scheduled_arrival_time": to_datetime(s["arrivo_teorico"]),
                "scheduled_departure_time": to_datetime(s["partenza_teorica"]),
                "scheduled_arrival_track": s["binarioProgrammatoArrivoDescrizione"],
                "actual_arrival_track": s["binarioEffettivoArrivoDescrizione"],
                "scheduled_departure_track": s["binarioProgrammatoPartenzaDescrizione"],
                "actual_departure_track": s["binarioEffettivoPartenzaDescrizione"],
            }
            for s in r["fermate"]
        ],
    )


@app.get("/stats", response_model=Stats, tags=["other"])
def get_stats() -> Stats:
    """Get statistics about today's circulating trains."""
    timestamp = int(datetime.now().timestamp() * 1000)
    r = get("statistiche", timestamp)

    return Stats(
        trains_since_midnight=r["treniGiorno"],
        trains_running=r["treniCircolanti"],
        last_update=to_datetime(r["ultimoAggiornamento"]),
    )


def to_ms_date_timestamp(date_to_convert: date | datetime | int | str) -> int:
    """Return the timestamp of the given date at midnight in milliseconds.

    The date can be a date, a datetime, a timestamp in milliseconds
    or a string in ISO 8601 format.
    """
    if isinstance(date_to_convert, date):
        converted_datetime = datetime.combine(date_to_convert, time.min)
    elif isinstance(date_to_convert, datetime):
        converted_datetime = datetime.combine(date_to_convert.date(), time.min)
    elif isinstance(date_to_convert, int):
        converted_datetime = datetime.fromtimestamp(date_to_convert / 1000)
        converted_datetime = datetime.combine(converted_datetime.date(), time.min)
    elif isinstance(date_to_convert, str):
        try:
            converted_datetime = datetime.fromisoformat(date_to_convert)
        except ValueError:
            msg = f"Invalid date format: {date_to_convert}"
            raise ValueError(msg) from None
    else:
        msg = f"Unsupported date type: {type(date_to_convert)}"
        raise TypeError(msg)

    return int(converted_datetime.timestamp() * 1000)


def to_string(datetime_to_convert: datetime | int | str) -> str:
    """Convert a datetime, timestamp, or ISO 8601 string to a string in the format used by ViaggiaTreno."""
    if isinstance(datetime_to_convert, int):
        datetime_to_convert = datetime.fromtimestamp(datetime_to_convert / 1000)
    elif isinstance(datetime_to_convert, str):
        datetime_to_convert = datetime.fromisoformat(datetime_to_convert)

    return datetime_to_convert.strftime("%a %b %d %Y %H:%M:%S")


def to_enee_code(station_id: str) -> int:
    """Strip the prefix from an ENEE code and return it as an integer.

    Most station IDs returned by ViaggiaTreno are ENEE codes prefixed with "S".
    For consistency, we strip the prefix and return only the code as an integer.
    """
    if station_id.startswith("S"):
        enee_code = int(station_id[1:])
    elif station_id.startswith("830"):
        enee_code = int(station_id[3:])
    else:
        enee_code = int(station_id)

    if enee_code < MIN_ENEE_CODE or enee_code > MAX_ENEE_CODE:
        msg = f"ENEE code must be a number of up to 5 digits, got {enee_code}"
        raise ValueError(msg)

    return enee_code


def to_station_id(enee_code: int) -> str:
    """Return a 6-digit station ID in the format used by ViaggiaTreno.

    ViaggiaTreno uses 6-digit station IDs, where the first digit is always "S".
    If the given ENEE code is less than 5 digits, it is zero-padded.
    """
    return f"S{enee_code:05d}"


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
