from datetime import date, datetime, time

import requests


class ViaggiaTrenoAPIWrapper:
    """A wrapper for the ViaggiaTreno API.

    As a general rule, station ids required as arguments are always
    in the form a an 'S' followed by the ENEE code of the station
    padded with zeroes until it's 5 digits long. The ids returned by
    this class' methods are always in this form.

    Departure and arrival times are always datetime objects and not
    time objects because otherwise it would be impossible compute a
    correct duration in every case.

    Train numbers are strings because they can contain letters (e.g. Urb)
    """

    BASE_URI = "http://www.viaggiatreno.it/infomobilita/resteasy/viaggiatreno"

    @classmethod
    def _get(cls, endpoint: str, *args: str) -> dict | str:
        url = f'{cls.BASE_URI}/{endpoint}/{"/".join(str(arg) for arg in args)}'
        r = requests.get(url, timeout=30)
        r.raise_for_status()

        return r.json() if "json" in r.headers["Content-Type"] else r.text

    @classmethod
    def get_statistics(cls) -> dict:
        """Return statistics about trains for today."""
        timestamp = int(datetime.now().timestamp() * 1000)
        r = cls._get("statistiche", timestamp)

        return {
            "trains_since_midnight": r.get("treniGiorno"),
            "trains_running": r.get("treniCircolanti"),
            "last_update": Utils.datetime_from_ms_timestamp(
                r.get("ultimoAggiornamento"),
            ),
        }

    @classmethod
    def get_stations_matching_prefix(cls, prefix: str) -> list[dict[str, str]]:
        """Return a list of stations starting with the given text."""
        r = cls._get("cercaStazione", prefix)

        return [{"name": s.get("nomeLungo"), "id": s.get("id")} for s in r]

    @classmethod
    def get_departures(
        cls,
        station_id: str,
        dt: datetime | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return the departures from a station at a certain time."""
        if dt is None:
            dt = datetime.now()

        dep_time = Utils.to_string(dt)
        r = cls._get("partenze", station_id, dep_time)

        return [
            {
                "category": d["categoriaDescrizione"].strip(),
                "number": d["numeroTreno"],
                "departure_date": Utils.date_from_ms_timestamp(d["dataPartenzaTreno"]),
                "origin_id": d["codOrigine"],
                "destination": d["destinazione"],
                "scheduled_track": d["binarioProgrammatoPartenzaDescrizione"],
                "actual_track": d["binarioEffettivoPartenzaDescrizione"],
                "departure_time": Utils.datetime_from_ms_timestamp(d["orarioPartenza"]),
                "departed_from_origin": not d["nonPartito"],
                "in_station": d["inStazione"],
                "delay": int(d["ritardo"]),
                "warning": d["subTitle"],
            }
            for i, d in enumerate(r)
            if i < limit
        ]

    @classmethod
    def get_arrivals(
        cls,
        station_id: str,
        dt: datetime | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """Return the arrivals to a station at a certain time."""
        if dt is None:
            dt = datetime.now()

        arr_time = Utils.to_string(dt)
        r = cls._get("arrivi", station_id, arr_time)

        arrivals = []
        for i, a in enumerate(r):
            if i == limit:
                break

            arrivals.append(
                {
                    "category": a["categoriaDescrizione"].strip(),
                    "number": a["numeroTreno"],
                    "departure_date": Utils.date_from_ms_timestamp(
                        a["dataPartenzaTreno"],
                    ),
                    "origin_id": a["codOrigine"],
                    "origin": a["origine"],
                    "scheduled_track": a["binarioProgrammatoArrivoDescrizione"],
                    "actual_track": a["binarioEffettivoArrivoDescrizione"],
                    "arrival_time": Utils.datetime_from_ms_timestamp(a["orarioArrivo"]),
                    "departed_from_origin": not a["nonPartito"],
                    "in_station": a["inStazione"],
                    "delay": int(
                        a["ritardo"],
                    ),  # Not as precise as the delay reported by get_train_progress
                    "warning": a["subTitle"],
                },
            )

        return arrivals

    @classmethod
    def get_train_info(cls, train_number: int) -> dict:
        # I should use the endpoint "cercaNumeroTrenoTrenoAutocomplete" (no typo)
        # in case there are multiple trains with the same number (e.g., REG 2347
        # from Milano Centrale)
        r = cls._get("cercaNumeroTreno", train_number)

        return {
            "number": r.get("numeroTreno"),
            "departure_date": Utils.date_from_ms_timestamp(r.get("dataPartenza")),
            "departure_station_id": r.get("codLocOrig"),
            "departure_station": r.get("descLocOrig"),
        }

    @classmethod
    def get_travel_solutions(
        cls,
        origin_id: str,
        dest_id: str,
        dt: datetime | None = None,
        limit: int = 10,
    ) -> dict:
        """Return travel solutions between two stations."""
        if dt is None:
            dt = datetime.now(datetime.now())

        origin_enee_code = Utils.get_enee_code(origin_id)
        destination_enee_code = Utils.get_enee_code(dest_id)
        r = cls._get(
            "soluzioniViaggioNew",
            origin_enee_code,
            destination_enee_code,
            dt.isoformat(),
        )

        solutions = {
            "origin": r["origine"],
            "destination": r["destinazione"],
            "solutions": [],
        }

        for i, s in enumerate(r["soluzioni"]):
            if i == limit:
                break

            vehicles = [
                {
                    "origin": v["origine"],
                    "destination": v["destinazione"],
                    "departure_time": datetime.fromisoformat(v["orarioPartenza"]),
                    "arrival_time": datetime.fromisoformat(v["orarioArrivo"]),
                    "category": v["categoriaDescrizione"],
                    "number": v["numeroTreno"],
                }
                for v in s["vehicles"]
            ]

            solutions["solutions"].append({"vehicles": vehicles})

        return solutions

    @classmethod
    def get_train_progress(
        cls,
        origin_id: str,
        train_number: int,
        dep_date: date,
    ) -> dict | None:
        """Return the progress of a train."""
        dep_date_ts: int = Utils.to_ms_date_timestamp(dep_date)
        r = cls._get("andamentoTreno", origin_id, train_number, dep_date_ts)

        if not r:
            return None

        train_number_changes = [
            {"new_train_number": c["nuovoNumeroTreno"], "station": c["stazione"]}
            for c in r["cambiNumero"]
        ]

        stops = [
            {
                "id": s.get("id"),
                "name": s.get("stazione"),
                "stop_type": s.get("tipoFermata"),
                "actual_arrival_time": Utils.datetime_from_ms_timestamp(
                    s["arrivoReale"],
                ),
                "actual_departure_time": Utils.datetime_from_ms_timestamp(
                    s["partenzaReale"],
                ),
                "arrived": Utils.datetime_from_ms_timestamp(s["arrivoReale"])
                is not None,
                "departed": Utils.datetime_from_ms_timestamp(s["partenzaReale"])
                is not None,
                "scheduled_arrival_time": Utils.datetime_from_ms_timestamp(
                    s.get("arrivo_teorico"),
                ),
                "scheduled_departure_time": Utils.datetime_from_ms_timestamp(
                    s.get("partenza_teorica"),
                ),
                "scheduled_arrival_track": s.get("binarioProgrammatoArrivoDescrizione"),
                "actual_arrival_track": s.get("binarioEffettivoArrivoDescrizione"),
                "scheduled_departure_track": s.get(
                    "binarioProgrammatoPartenzaDescrizione",
                ),
                "actual_departure_track": s.get("binarioEffettivoPartenzaDescrizione"),
            }
            for s in r["fermate"]
        ]

        # Check fermateSoppresse, tipoTreno and motivoRitardoPrevalente
        # There's a numeroTreno which is an int here
        return {
            "last_update_time": Utils.datetime_from_ms_timestamp(
                r.get("oraUltimoRilevamento"),
            ),
            "last_update_station": (
                s if (s := r.get("stazioneUltimoRilevamento")) != "--" else None
            ),
            "train_type": r.get("tipoTreno"),
            "category": r.get("categoria"),
            "number": str(r.get("numeroTreno")),
            "departure_date": Utils.date_from_ms_timestamp(r.get("dataPartenzaTreno")),
            "origin_id": r.get("idOrigine"),
            "origin": r.get("origine"),
            "destination": r.get("destinazione"),
            "destination_id": r.get("idDestinazione"),
            "train_number_changes": train_number_changes,
            "departure_time": Utils.datetime_from_ms_timestamp(r.get("orarioPartenza")),
            "arrival_time": Utils.datetime_from_ms_timestamp(r.get("orarioArrivo")),
            "departed_from_origin": not r.get("nonPartito"),
            "in_station": r.get("inStazione"),
            "delay": int(r.get("ritardo") or 0),
            "warning": r.get("subTitle"),
            "delay_reason": r.get("motivoRitardoPrevalente"),
            "stops": stops,
        }


class Utils:
    """A collection of utility functions."""

    @classmethod
    def to_ms_date_timestamp(cls, date_to_convert: date | datetime | int | str) -> int:
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

    @classmethod
    def to_string(cls, dt: datetime | int | str) -> str:
        if isinstance(dt, int):
            dt = datetime.fromtimestamp(dt / 1000)
        elif isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        return dt.strftime("%a %b %d %Y %H:%M:%S")

    @classmethod
    def get_enee_code(cls, station_id: str) -> int:
        if len(station_id) == 6:  # noqa: PLR2004
            enee_code = int(station_id.lstrip("S"))
        elif len(station_id) == 8:  # noqa: PLR2004
            enee_code = int(station_id.lstrip("830"))
        else:
            enee_code = int(station_id)

        if not (0 <= enee_code <= 99999):  # noqa: PLR2004
            msg = "Station ID must be a 5 digit integer"
            raise ValueError(msg)

        return enee_code

    @classmethod
    def datetime_from_ms_timestamp(cls, timestamp_ms: int | None) -> datetime | None:
        if timestamp_ms is None:
            return None

        return datetime.fromtimestamp(timestamp_ms / 1000)

    @classmethod
    def date_from_ms_timestamp(cls, timestamp_ms: int | None) -> date | None:
        if timestamp_ms is None:
            return None

        return datetime.fromtimestamp(timestamp_ms / 1000).date()
