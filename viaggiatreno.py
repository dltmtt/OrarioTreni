from datetime import date, datetime, time

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="ViaggiaTreno API Wrapper",
    description="An API wrapper for ViaggiaTreno, the official Trenitalia API.",
)

BASE_URI = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"


def _get(endpoint: str, *args: str) -> dict | str:
    url = f'{BASE_URI}/{endpoint}/{"/".join(str(arg) for arg in args)}'
    r = requests.get(url, timeout=30)
    r.raise_for_status()

    return r.json() if "json" in r.headers["Content-Type"] else r.text


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
    in_station: bool
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
    in_station: bool
    delay: int
    warning: str | None


class TrainInfo(BaseModel):
    number: int
    departure_date: date
    origin_enee_code: int
    origin: str


class TravelSolution(BaseModel):
    origin: str
    destination: str
    solutions: list[dict]


class TrainStop(BaseModel):
    enee_code: str
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
    number: str
    departure_date: date
    origin_enee_code: int
    origin: str
    destination: str
    destination_enee_code: int
    train_number_changes: list[dict]
    departure_time: datetime
    arrival_time: datetime
    departed_from_origin: bool
    in_station: bool
    delay: int
    warning: str
    delay_reason: str | None
    stops: list[TrainStop]


@app.get("/stats", response_model=Stats)
def get_stats() -> Stats:
    """Return statistics about trains for today."""
    timestamp = int(datetime.now().timestamp() * 1000)
    r = _get("statistiche", timestamp)

    return Stats(
        trains_since_midnight=r["treniGiorno"],
        trains_running=r["treniCircolanti"],
        last_update=datetime_from_ms_timestamp(r["ultimoAggiornamento"]),
    )


@app.get("/stations/search/{prefix}", response_model=list[BaseStation])
def get_stations_matching_prefix(prefix: str) -> list[BaseStation]:
    """Return a list of stations starting with the given text."""
    r = _get("cercaStazione", prefix)

    if not r:
        raise HTTPException(
            status_code=404,
            detail="No stations matching the given prefix could be found",
        )

    return [
        BaseStation(name=s["nomeLungo"], enee_code=get_unprefixed_enee_code(s["id"]))
        for s in r
    ]


@app.get("/stations/{enee_code}/departures", response_model=list[Departure])
def get_departures(
    enee_code: int,
    search_datetime: datetime | None = None,
    limit: int = 10,
) -> list[Departure]:
    """Return the departures from a station at a certain time."""
    if search_datetime is None:
        search_datetime = datetime.now()

    departure_datetime = to_string(search_datetime)
    r = _get("partenze", get_prefixed_enee_code(enee_code), departure_datetime)

    return [
        Departure(
            category=d["categoriaDescrizione"].strip(),
            number=d["numeroTreno"],
            departure_date=date_from_ms_timestamp(d["dataPartenzaTreno"]),
            origin_enee_code=get_unprefixed_enee_code(d["codOrigine"]),
            destination=d["destinazione"],
            scheduled_track=d.get("binarioProgrammatoPartenzaDescrizione"),
            actual_track=d.get("binarioEffettivoPartenzaDescrizione"),
            departure_time=datetime_from_ms_timestamp(d["orarioPartenza"]),
            departed_from_origin=not d["nonPartito"],
            in_station=d["inStazione"],
            delay=int(d["ritardo"]),
            warning=d.get("subTitle"),
        )
        for d in r[:limit]
    ]


@app.get("/stations/{enee_code}/arrivals", response_model=list[Arrival])
def get_arrivals(
    enee_code: int,
    search_datetime: datetime | None = None,
    limit: int = 10,
) -> list[Arrival]:
    """Return the arrivals to a station at a certain time."""
    if search_datetime is None:
        search_datetime = datetime.now()

    arrival_datetime = to_string(search_datetime)
    r = _get("arrivi", get_prefixed_enee_code(enee_code), arrival_datetime)

    return [
        Arrival(
            category=a["categoriaDescrizione"].strip(),
            number=a["numeroTreno"],
            departure_date=date_from_ms_timestamp(a["dataPartenzaTreno"]),
            origin_enee_code=get_unprefixed_enee_code(a["codOrigine"]),
            origin=a["origine"],
            scheduled_track=a["binarioProgrammatoArrivoDescrizione"],
            actual_track=a["binarioEffettivoArrivoDescrizione"],
            arrival_time=datetime_from_ms_timestamp(a["orarioArrivo"]),
            departed_from_origin=not a["nonPartito"],
            in_station=a["inStazione"],
            delay=int(a["ritardo"]),
            warning=a["subTitle"],
        )
        for a in r[:limit]
    ]


@app.get("/trains/{train_number}", response_model=TrainInfo)
def get_train_info(train_number: int) -> TrainInfo:
    # TODO: I should use the endpoint "cercaNumeroTrenoTrenoAutocomplete" (no typo)
    # in case there are multiple trains with the same number (e.g., REG 2347
    # from Milano Centrale)
    r = _get("cercaNumeroTreno", train_number)

    return TrainInfo(
        number=r["numeroTreno"],
        departure_date=date_from_ms_timestamp(r["dataPartenza"]),
        origin_enee_code=get_unprefixed_enee_code(r["codLocOrig"]),
        origin=r["descLocOrig"],
    )


@app.get("/search", response_model=TravelSolution)
def get_travel_solutions(
    origin_enee_code: int,
    destination_enee_code: int,
    search_datetime: datetime | None = None,
    limit: int = 10,
) -> TravelSolution:
    """Return travel solutions between two stations."""
    if search_datetime is None:
        search_datetime = datetime.now()

    r = _get(
        "soluzioniViaggioNew",
        origin_enee_code,
        destination_enee_code,
        search_datetime.isoformat(),
    )

    return TravelSolution(
        origin=r["origine"],
        destination=r["destinazione"],
        solutions=[
            {
                "vehicles": [
                    {
                        "origin": v["origine"],
                        "destination": v["destinazione"],
                        "departure_time": datetime.fromisoformat(v["orarioPartenza"]),
                        "arrival_time": datetime.fromisoformat(v["orarioArrivo"]),
                        "category": v["categoriaDescrizione"],
                        "number": v["numeroTreno"],
                    }
                    for v in s["vehicles"]
                ],
            }
            for s in r["soluzioni"][:limit]
        ],
    )


@app.get("/trains", response_model=TrainProgress | None)
def get_train_progress(
    origin_enee_code: int,
    train_number: int,
    departure_date: date,
) -> TrainProgress | None:
    """Return the progress of a train."""
    dep_date_ts: int = to_ms_date_timestamp(departure_date)
    r = _get(
        "andamentoTreno",
        get_prefixed_enee_code(origin_enee_code),
        train_number,
        dep_date_ts,
    )

    if not r:
        return None

    return TrainProgress(
        last_update_time=datetime_from_ms_timestamp(r["oraUltimoRilevamento"]),
        last_update_station=r["stazioneUltimoRilevamento"]
        if r["stazioneUltimoRilevamento"] != "--"
        else None,
        train_type=r["tipoTreno"],
        category=r["categoria"],
        number=str(r["numeroTreno"]),
        departure_date=date_from_ms_timestamp(r["dataPartenzaTreno"]),
        origin_enee_code=get_unprefixed_enee_code(r["idOrigine"]),
        origin=r["origine"],
        destination=r["destinazione"],
        destination_enee_code=get_unprefixed_enee_code(r["idDestinazione"]),
        train_number_changes=[
            {"new_train_number": c["nuovoNumeroTreno"], "station": c["stazione"]}
            for c in r["cambiNumero"]
        ],
        departure_time=datetime_from_ms_timestamp(r["orarioPartenza"]),
        arrival_time=datetime_from_ms_timestamp(r["orarioArrivo"]),
        departed_from_origin=not r["nonPartito"],
        in_station=r["inStazione"],
        delay=int(r["ritardo"] or 0),
        warning=r["subTitle"],
        delay_reason=r["motivoRitardoPrevalente"],
        stops=[
            {
                "enee_code": s["id"],
                "name": s["stazione"],
                "stop_type": map_stop_type(s["tipoFermata"]),
                "actual_arrival_time": datetime_from_ms_timestamp(s["arrivoReale"]),
                "actual_departure_time": datetime_from_ms_timestamp(s["partenzaReale"]),
                "arrived": datetime_from_ms_timestamp(s["arrivoReale"]) is not None,
                "departed": datetime_from_ms_timestamp(s["partenzaReale"]) is not None,
                "scheduled_arrival_time": datetime_from_ms_timestamp(
                    s["arrivo_teorico"],
                ),
                "scheduled_departure_time": datetime_from_ms_timestamp(
                    s["partenza_teorica"],
                ),
                "scheduled_arrival_track": s["binarioProgrammatoArrivoDescrizione"],
                "actual_arrival_track": s["binarioEffettivoArrivoDescrizione"],
                "scheduled_departure_track": s["binarioProgrammatoPartenzaDescrizione"],
                "actual_departure_track": s["binarioEffettivoPartenzaDescrizione"],
            }
            for s in r["fermate"]
        ],
    )


def to_ms_date_timestamp(date_to_convert: date | datetime | int | str) -> int:
    """Return the timestamp of the given date at midnight in milliseconds.

    The date can be a date, a datetime, a timestamp in milliseconds
    or a string in ISO 8601 format.
    """
    if isinstance(date_to_convert, date):
        dt = datetime.combine(date_to_convert, time.min)
    elif isinstance(date_to_convert, datetime):
        dt = datetime.combine(date_to_convert.date(), time.min)
    elif isinstance(date_to_convert, int):
        dt = datetime.fromtimestamp(date_to_convert / 1000)
        dt = datetime.combine(dt.date(), time.min)
    elif isinstance(date_to_convert, str):
        try:
            dt = datetime.fromisoformat(date_to_convert)
        except ValueError:
            msg = f"Invalid date format: {date_to_convert}"
            raise ValueError(msg) from None
    else:
        msg = f"Unsupported date type: {type(date_to_convert)}"
        raise TypeError(msg)

    return int(dt.timestamp() * 1000)


def to_string(dt: datetime | int | str) -> str:
    if isinstance(dt, int):
        dt = datetime.fromtimestamp(dt / 1000)
    elif isinstance(dt, str):
        dt = datetime.fromisoformat(dt)

    return dt.strftime("%a %b %d %Y %H:%M:%S")


def get_unprefixed_enee_code(prefixed_enee_code: str) -> int:
    if len(prefixed_enee_code) == 6:  # noqa: PLR2004
        enee_code = int(prefixed_enee_code.lstrip("S"))
    elif len(prefixed_enee_code) == 8:  # noqa: PLR2004
        enee_code = int(prefixed_enee_code.lstrip("830"))
    else:
        enee_code = int(prefixed_enee_code)

    if not (0 <= enee_code <= 99999):  # noqa: PLR2004
        msg = "enee_code must be a 5-digit number"
        raise ValueError(msg)

    return enee_code


def get_prefixed_enee_code(unprefixed_enee_code: int) -> str:
    return f"S{unprefixed_enee_code:05d}"


def datetime_from_ms_timestamp(timestamp_ms: int | None) -> datetime | None:
    if timestamp_ms is None:
        return None

    return datetime.fromtimestamp(timestamp_ms / 1000)


def date_from_ms_timestamp(timestamp_ms: int | None) -> date | None:
    if timestamp_ms is None:
        return None

    return datetime.fromtimestamp(timestamp_ms / 1000).date()


def map_stop_type(stop_type: str) -> str:
    return {
        "P": "departure",
        "F": "intermediate",
        "A": "arrival",
    }.get(stop_type, stop_type)
