#!/usr/bin/env python3

__version__ = "0.2"
__author__ = "Matteo Delton"

import logging
import sys
from argparse import ArgumentParser, BooleanOptionalAction
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta

import inquirer
from prettytable import PrettyTable

from ansicolors import Foreground as F
from ansicolors import Style as S
from viaggiatreno import ViaggiaTrenoAPIWrapper as API

# pylint: disable=fixme, missing-class-docstring


class Train:
    """
    Represents a train, which is identified by the triple (number, origin_id, departure_date).
    """

    def __init__(self, number: int, origin_id: str, departure_date: date):
        self.number: int = number
        self.departure_station: str = origin_id
        self.departure_date: date = departure_date

        progress = API.get_train_progress(origin_id, number, departure_date)
        if not progress:
            return

        self.last_update_station: str | None = progress.get("last_update_station")
        self.last_update_time: datetime | None = progress.get("last_update_time")

        self.category: str = progress["category"]
        self.number_changes: list[dict[str, str]] = progress["train_number_changes"]

        self.stops: list[Station] = [
            Station(s["id"], s["name"], self, progress["stops"])
            for s in progress["stops"]
        ]
        self.origin = self.stops[0]
        self.destination = self.stops[-1]

        self.departure_time: datetime = progress["departure_time"]  # w.r.t. the origin
        self.arrival_time: datetime = progress["arrival_time"]  # w.r.t. the destination
        self.departed_from_origin: bool = progress["departed_from_origin"]
        self.delay: int = progress["delay"]

    def __str__(self):
        numbers = str(self.number)
        if self.number_changes:
            numbers += "/"
            numbers += "/".join(c["new_train_number"] for c in self.number_changes)

        if self.category:
            return f"{self.category} {numbers}"
        return f"{numbers}"

    def __repr__(self):
        return f"Train({self.number}, {self.departure_station}, {self.departure_date})"

    def get_formatted_delay(self) -> str:
        # TODO: decide whether to use self.departed_from_origin or self.origin.departed
        if self.origin.departed:
            if self.delay > 0:
                return F.red(f"{self.delay:+}")
            if self.delay < 0:
                return F.green(f"{self.delay:+}")
            return "In orario"

        if self.origin.actual_departure_track is not None:
            return "In stazione"

        return "Non partito"

    def show_progress(self) -> None:
        print(
            f"Treno {self} · {self.get_formatted_delay()}\n"
            f"{self.departure_time.strftime('%H:%M')} {self.origin.name}\n"
            f"{self.arrival_time.strftime('%H:%M')} {self.destination.name}"
        )

        if self.last_update_station is not None and self.last_update_time is not None:
            print(
                f"{S.DIM}Ultimo aggiornamento alle {self.last_update_time.strftime('%H:%M')}"
                f" a {self.last_update_station}{S.NORMAL}"
            )
        else:
            print(
                f"{S.DIM}Non sono disponibili aggiornamenti per questo treno.{S.NORMAL}"
            )

        for stop in self.stops:
            track = stop.get_formatted_track()

            if track:
                print(f"\n{stop.name} · {track}")
            else:
                print(f"\n{stop.name}")

            if stop.type in ("P", "F"):
                print(
                    f"Dep.:\t{stop.scheduled_departure_time.strftime("%H:%M")}"
                    f"\t{stop.get_formatted_time(self.delay, True)}"
                )

            if stop.type in ("A", "F"):
                print(
                    f"Arr.:\t{stop.scheduled_arrival_time.strftime('%H:%M')}"
                    f"\t{stop.get_formatted_time(self.delay, False)}"
                )


class Station:
    """
    Represents a station, possibly intended as a stop for a specific train.
    """

    # TODO: remove stops dict
    def __init__(
        self,
        prefixed_enee_code: str,
        name: str,
        train: Train | None = None,
        stops: dict | None = None,
    ):
        self.prefixed_enee_code: str = prefixed_enee_code
        self.name: str = name

        if train is None or stops is None:
            return

        self.train = train

        stop = next((s for s in stops if s["id"] == self.prefixed_enee_code), None)
        if stop is None:
            return

        self.actual_departure_track: str = stop.get("actual_departure_track")
        self.scheduled_departure_track: str = stop.get("scheduled_departure_track")
        self.actual_arrival_track: str = stop.get("actual_arrival_track")
        self.scheduled_arrival_track: str = stop.get("scheduled_arrival_track")
        self.arrived: bool = stop.get("arrived")
        self.departed: bool = stop.get("departed")

        self.type: str = stop.get("stop_type")

        self.actual_departure_time: datetime = stop.get("actual_departure_time")
        self.scheduled_departure_time: datetime = stop.get("scheduled_departure_time")
        self.actual_arrival_time: datetime = stop.get("actual_arrival_time")
        self.scheduled_arrival_time: datetime = stop.get("scheduled_arrival_time")

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Station({self.prefixed_enee_code}, {self.name})"

    def show_timetable(
        self, timetable_datetime=datetime.now(), limit=10, is_departure=True
    ):
        print(S.bold(f"{"Partenze da" if is_departure else "Arrivi a"} {self.name}"))

        table = PrettyTable()

        if is_departure:
            trains: list[dict] = API.get_departures(
                self.prefixed_enee_code, timetable_datetime, limit
            )
            if not trains:
                print("Nessun treno in partenza nei prossimi 90 minuti.")
                return
            table.field_names = [
                "Treno",
                "Destinazione",
                "Partenza",
                "Ritardo",
                "Binario",
            ]
        else:
            trains: list[dict] = API.get_arrivals(
                self.prefixed_enee_code, timetable_datetime, limit
            )
            if not trains:
                print("Nessun treno in arrivo nei prossimi 90 minuti.")
                return
            table.field_names = ["Treno", "Origine", "Arrivo", "Ritardo", "Binario"]

        with ThreadPoolExecutor(max_workers=len(trains)) as executor:
            futures = [
                executor.submit(
                    self.process_train,
                    Train(train["number"], train["origin_id"], train["departure_date"]),
                    is_departure,
                )
                for train in trains
            ]

            for future in futures:
                row = future.result()
                table.add_row(row)

        print(table)

    def process_train(self, train: Train, checking_for_departures: bool) -> list:
        station = next(
            (s for s in train.stops if s.prefixed_enee_code == self.prefixed_enee_code),
            None,
        )

        if station is None:
            raise ValueError("Non-real-time updates not implemented yet")

        if checking_for_departures:
            station_name = train.destination.name
            scheduled_time = station.scheduled_departure_time.strftime("%H:%M")
        else:
            station_name = train.origin.name
            scheduled_time = station.scheduled_arrival_time.strftime("%H:%M")

        precise_data = [
            train,
            station_name,
            scheduled_time,
            train.get_formatted_delay(),  # TODO: Should get the delay for this specific station?
            station.get_formatted_track(),
        ]

        return precise_data

    def get_formatted_track(self) -> str:
        track = self.actual_departure_track or self.actual_arrival_track
        scheduled_track = self.scheduled_departure_track or self.scheduled_arrival_track

        if track:
            if track == scheduled_track:
                track = F.blue(track)
            elif scheduled_track:
                track = F.magenta(track)
            else:
                track = F.cyan(track)
        else:
            track = scheduled_track

        if (self.arrived or self.train.origin.actual_departure_time) and (
            self.departed or self.train.destination.actual_arrival_time
        ):
            track = S.dim(track)
        elif self.arrived and not self.departed:
            track = S.bold(track)

        return track

    def get_formatted_time(
        self, delay: int, checking_for_departures: bool
    ) -> str | None:
        actual_time = (
            self.actual_departure_time
            if checking_for_departures
            else self.actual_arrival_time
        )
        scheduled_time = (
            self.scheduled_departure_time
            if checking_for_departures
            else self.scheduled_arrival_time
        )

        if actual_time:
            if actual_time > scheduled_time + timedelta(seconds=30):
                formatted_time = F.red(actual_time.strftime("%H:%M"))
            else:
                formatted_time = F.green(actual_time.strftime("%H:%M"))
        else:
            if delay > 0:
                formatted_time = F.yellow(
                    (scheduled_time + timedelta(minutes=delay)).strftime("%H:%M")
                )
            else:
                formatted_time = scheduled_time.strftime("%H:%M")

        return formatted_time


def show_statistics():
    s = API.get_statistics()

    print(
        f"Treni in circolazione da mezzanotte: {s['trains_since_midnight']}\n"
        f"Treni in circolazione ora: {s['trains_running']}\n"
        f"{S.DIM}Ultimo aggiornamento: {s['last_update'].strftime('%T')}{S.NORMAL}"
    )


def choose_station(station_prefix: str) -> Station | None:
    stations: list[dict[str, str]] = API.get_stations_matching_prefix(station_prefix)

    if not stations:
        return None

    if len(stations) == 1:
        return Station(stations[0]["id"], stations[0]["name"])

    guesses = [(s["name"], s["id"]) for s in stations]
    chosen_station_id = inquirer.list_input(
        message="Seleziona la stazione", choices=guesses
    )

    return Station(
        chosen_station_id,
        next((s["name"] for s in stations if s["id"] == chosen_station_id)),
    )


if __name__ == "__main__":
    ap = ArgumentParser(description="Get information about trains in Italy")

    ap.add_argument(
        "-v", "--version", action="version", version=f"%(prog)s {__version__}"
    )
    ap.add_argument(
        "-d",
        "--departures",
        metavar="STATION",
        type=str,
        help="show departures from STATION",
    )
    ap.add_argument(
        "-a",
        "--arrivals",
        metavar="STATION",
        type=str,
        help="show arrivals to STATION",
    )
    ap.add_argument(
        "-n",
        "--train-number",
        metavar="NUMBER",
        type=int,
        help="show progress of train NUMBER",
    )
    ap.add_argument(
        "-s",
        "--solutions",
        metavar=("DEPARTURE", "ARRIVAL"),
        type=str,
        nargs=2,
        help="show journey solutions from DEPARTURE to ARRIVAL",
    )
    ap.add_argument(
        "--date",
        metavar="YYYY-MM-DD",
        type=str,
        help="date to use for the other actions (defaults to today)",
        default=datetime.now().date().strftime("%Y-%m-%d"),
    )
    ap.add_argument(
        "--time",
        metavar="HH:MM",
        type=str,
        help="time to use for the other actions (defaults to now)",
        default=datetime.now().time().strftime("%H:%M"),
    )
    ap.add_argument(
        "--limit",
        metavar="N",
        type=int,
        help="limit the number of results to N (defaults to 10)",
        default=10,
    )
    ap.add_argument(
        "--stats",
        action=BooleanOptionalAction,
        help="show/don't show statistics about trains (defaults to False)",
        default=False,
    )
    ap.add_argument(
        "--log-level",
        metavar="LEVEL",
        type=str,
        help="set the logging level (defaults to WARNING)",
        default="WARNING",
    )

    ap.epilog = (
        "Departures and arrivals show trains from/to the selected "
        "station in a range from 15 minutes before to 90 minutes after "
        "the selected time."
    )

    args = ap.parse_args()

    if args.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        print(
            f"Invalid log level: {F.red(args.log_level)} "
            "(valid values are: DEBUG, INFO, WARNING, ERROR, CRITICAL)."
        )

        sys.exit(1)

    logging.basicConfig(level=args.log_level)

    if args.stats:
        show_statistics()

    search_date: date = datetime.strptime(args.date, "%Y-%m-%d").date()
    search_time: time = datetime.strptime(args.time, "%H:%M").time()
    search_datetime: datetime = datetime.combine(search_date, search_time)

    if args.departures:
        if (queried_station := choose_station(args.departures)) is None:
            print("Nessuna stazione trovata", file=sys.stderr)
            sys.exit(1)
        queried_station.show_timetable(search_datetime, args.limit, True)

    if args.arrivals:
        if (queried_station := choose_station(args.arrivals)) is None:
            print("Nessuna stazione trovata", file=sys.stderr)
            sys.exit(1)
        queried_station.show_timetable(search_datetime, args.limit, False)

    if args.train_number:
        # TODO: handle multiple trains with the same number
        train_info: dict = API.get_train_info(args.train_number)
        train_to_monitor: Train = Train(
            train_info["number"],
            train_info["departure_station_id"],
            train_info["departure_date"],
        )
        train_to_monitor.show_progress()

    if args.solutions:
        print("Not implemented yet")
