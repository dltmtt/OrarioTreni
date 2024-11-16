#!/usr/bin/env python3

__version__ = "0.2.0"

import logging
import sys
from argparse import ArgumentParser, BooleanOptionalAction
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta

import inquirer
from prettytable import PrettyTable

import viaggiatreno as vt
from ansicolors import Foreground, Style
from viaggiatreno import (
    Arrival,
    BaseStation,
    Departure,
    TrainInfo,
    TrainStop,
)


class Train:
    """A train is identified by the triple (number, origin_enee_code, departure_date)."""

    def __init__(
        self,
        number: int,
        origin_enee_code: int,
        departure_date: date,
    ) -> None:
        self.number: int = number
        self.origin_enee_code: int = origin_enee_code
        self.departure_date: date = departure_date

        progress = vt.get_train_progress(origin_enee_code, number, departure_date)
        if not progress:
            return

        self.last_update_station: str | None = progress.last_update_station
        self.last_update_time: datetime | None = progress.last_update_time

        self.category: str = progress.category
        self.number_changes: list[dict[str, str]] = progress.train_number_changes

        self.stops: list[Station] = [
            Station(
                vt.get_unprefixed_enee_code(s.enee_code),
                s.name,
                self,
                progress.stops,
            )
            for s in progress.stops
        ]
        self.origin: Station = self.stops[0]
        self.destination: Station = self.stops[-1]
        self.departure_time: datetime = progress.departure_time
        self.arrival_time: datetime = progress.arrival_time
        self.departed_from_origin: bool = progress.departed_from_origin
        self.delay: int = progress.delay

    def __str__(self) -> str:
        numbers = str(self.number)
        if self.number_changes:
            numbers += "/"
            numbers += "/".join(c["new_train_number"] for c in self.number_changes)

        if self.category:
            return f"{self.category} {numbers}"
        return f"{numbers}"

    def __repr__(self) -> str:
        return f"Train({self.number}, {self.origin_enee_code}, {self.departure_date})"

    def get_formatted_delay(self) -> str:
        if self.origin.departed:
            if self.delay > 0:
                return Foreground.red(f"{self.delay:+}")
            if self.delay < 0:
                return Foreground.green(f"{self.delay:+}")
            return "In orario"

        if self.origin.actual_departure_track is not None:
            return "Pronto"

        return "Non partito"

    def show_progress(self) -> None:
        print(
            f"Treno {self} · {self.get_formatted_delay()}\n"
            f"{self.departure_time.strftime('%H:%M')} {self.origin.name}\n"
            f"{self.arrival_time.strftime('%H:%M')} {self.destination.name}",
        )

        if self.last_update_station is not None and self.last_update_time is not None:
            last_update_time = self.last_update_time.strftime("%H:%M")
            print(
                f"{Style.DIM}Ultimo aggiornamento alle {last_update_time}"
                f" a {self.last_update_station}{Style.NORMAL}",
            )
        else:
            print(f"{Style.DIM}Nessun aggiornamento disponibile.{Style.NORMAL}")

        for stop in self.stops:
            track = stop.get_formatted_track()

            if track:
                print(f"\n{stop.name} · {track}")
            else:
                print(f"\n{stop.name}")
            if stop.type in ("departure", "intermediate"):
                print(
                    f"Dep.:\t{stop.scheduled_departure_time.strftime('%H:%M')}"
                    f"\t{stop.get_formatted_time(self.delay, check_departures=True)}",
                )

            if stop.type in ("arrival", "intermediate"):
                print(
                    f"Arr.:\t{stop.scheduled_arrival_time.strftime('%H:%M')}"
                    f"\t{stop.get_formatted_time(self.delay, check_departures=False)}",
                )


class Station:
    """Represents a station, possibly intended as a stop for a specific train."""

    def __init__(
        self,
        enee_code: int,
        name: str,
        train: Train | None = None,
        stops: list[TrainStop] | None = None,
    ) -> None:
        self.enee_code: int = enee_code
        self.name: str = name

        if train is None or stops is None:
            return

        self.train = train

        stop = next(
            (
                s
                for s in stops
                if vt.get_unprefixed_enee_code(s.enee_code) == self.enee_code
            ),
            None,
        )
        if stop is None:
            return

        self.actual_departure_track: str | None = stop.actual_departure_track
        self.scheduled_departure_track: str | None = stop.scheduled_departure_track
        self.actual_arrival_track: str | None = stop.actual_arrival_track
        self.scheduled_arrival_track: str | None = stop.scheduled_arrival_track
        self.arrived: bool = stop.arrived
        self.departed: bool = stop.departed
        self.type: str = stop.stop_type
        self.actual_departure_time: datetime | None = stop.actual_departure_time
        self.scheduled_departure_time: datetime | None = stop.scheduled_departure_time
        self.actual_arrival_time: datetime | None = stop.actual_arrival_time
        self.scheduled_arrival_time: datetime | None = stop.scheduled_arrival_time

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Station({self.enee_code}, {self.name})"

    def show_timetable(
        self,
        timetable_datetime: datetime | None = None,
        limit: int = 10,
        *,
        is_departure: bool = True,
    ) -> None:
        if timetable_datetime is None:
            timetable_datetime = datetime.now()
        print(
            Style.bold(f"{'Partenze da' if is_departure else 'Arrivi a'} {self.name}"),
        )

        table = PrettyTable()

        if is_departure:
            trains: list[Departure] = vt.get_departures(
                self.enee_code,
                timetable_datetime,
                limit,
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
            trains: list[Arrival] = vt.get_arrivals(
                self.enee_code,
                timetable_datetime,
                limit,
            )
            if not trains:
                print("Nessun treno in arrivo nei prossimi 90 minuti.")
                return
            table.field_names = ["Treno", "Origine", "Arrivo", "Ritardo", "Binario"]

        with ThreadPoolExecutor(max_workers=len(trains)) as executor:
            futures = [
                executor.submit(
                    self.process_train,
                    Train(train.number, train.origin_enee_code, train.departure_date),
                    check_departures=is_departure,
                )
                for train in trains
            ]

            for future in futures:
                row = future.result()
                table.add_row(row)

        print(table)

    def process_train(self, train: Train, *, check_departures: bool) -> list:
        station = next(
            (s for s in train.stops if s.enee_code == self.enee_code),
            None,
        )

        if station is None:
            msg = "Non-real-time updates not implemented yet"
            raise NotImplementedError(msg)

        if check_departures:
            station_name = train.destination.name
            scheduled_time = station.scheduled_departure_time.strftime("%H:%M")
        else:
            station_name = train.origin.name
            scheduled_time = station.scheduled_arrival_time.strftime("%H:%M")

        return [
            train,
            station_name,
            scheduled_time,
            train.get_formatted_delay(),
            station.get_formatted_track(),
        ]

    def get_formatted_track(self) -> str:
        track = self.actual_departure_track or self.actual_arrival_track
        scheduled_track = self.scheduled_departure_track or self.scheduled_arrival_track

        if track:
            if track == scheduled_track:
                track = Foreground.blue(track)
            elif scheduled_track:
                track = Foreground.magenta(track)
            else:
                track = Foreground.cyan(track)
        else:
            track = scheduled_track

        if (self.arrived or self.train.origin.actual_departure_time) and (
            self.departed or self.train.destination.actual_arrival_time
        ):
            track = Style.dim(track)
        elif self.arrived and not self.departed:
            track = Style.bold(track)

        if track is None:
            return "N/A"

        return track

    def get_formatted_time(
        self,
        delay: int,
        *,
        check_departures: bool,
    ) -> str | None:
        actual_time = (
            self.actual_departure_time if check_departures else self.actual_arrival_time
        )
        scheduled_time = (
            self.scheduled_departure_time
            if check_departures
            else self.scheduled_arrival_time
        )

        if actual_time:
            if actual_time > scheduled_time + timedelta(seconds=30):
                formatted_time = Foreground.red(actual_time.strftime("%H:%M"))
            else:
                formatted_time = Foreground.green(actual_time.strftime("%H:%M"))
        elif delay > 0:
            formatted_time = Foreground.yellow(
                (scheduled_time + timedelta(minutes=delay)).strftime("%H:%M"),
            )
        else:
            formatted_time = scheduled_time.strftime("%H:%M")

        return formatted_time


def show_statistics() -> None:
    s = vt.get_stats()

    print(
        f"Treni in circolazione da mezzanotte: {s.trains_since_midnight}\n"
        f"Treni in circolazione ora: {s.trains_running}\n"
        f"{Style.DIM}Ultimo aggiornamento: {s.last_update.strftime('%T')}{Style.NORMAL}",
    )


def choose_station(station_prefix: str) -> Station | None:
    try:
        stations: list[BaseStation] = vt.get_stations_matching_prefix(station_prefix)
    except vt.HTTPException as e:
        print(e, file=sys.stderr)
        return None

    if len(stations) == 1:
        return Station(stations[0].enee_code, stations[0].name)

    guesses: list[tuple[str, int]] = [(s.name, s.enee_code) for s in stations]
    chosen_station_enee_code: int = inquirer.list_input(
        message="Seleziona la stazione",
        choices=guesses,
    )

    return Station(
        chosen_station_enee_code,
        next(s.name for s in stations if s.enee_code == chosen_station_enee_code),
    )


if __name__ == "__main__":
    ap = ArgumentParser(description="Get information about trains in Italy")

    ap.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
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
            f"Invalid log level: {Foreground.red(args.log_level)} "
            "(valid values are: DEBUG, INFO, WARNING, ERROR, CRITICAL).",
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
            sys.exit(1)
        queried_station.show_timetable(search_datetime, args.limit, is_departure=True)

    if args.arrivals:
        if (queried_station := choose_station(args.arrivals)) is None:
            sys.exit(1)
        queried_station.show_timetable(search_datetime, args.limit, is_departure=False)

    if args.train_number:
        train_info: list[TrainInfo] = vt.get_trains_with_number(args.train_number)

        if len(train_info) == 1:
            train_to_monitor: Train = Train(
                train_info[0].number,
                train_info[0].origin_enee_code,
                train_info[0].departure_date,
            )
        elif len(train_info) > 1:
            print("Treni trovati con lo stesso numero:")
            print(train_info)
            for train in train_info:
                print(f"{train.origin_name} - {train.departure_date}")
            chosen_train = inquirer.list_input(
                message="Seleziona il treno",
                choices=[
                    (f"{t.origin_name} - {t.departure_date}", t) for t in train_info
                ],
            )
            train_to_monitor: Train = Train(
                chosen_train.number,
                chosen_train.origin_enee_code,
                chosen_train.departure_date,
            )
        else:
            print(f"Nessun treno trovato con il numero {args.train_number}.")
            sys.exit(1)

        train_to_monitor.show_progress()

    if args.solutions:
        msg = "Journey solutions not implemented yet"
        raise NotImplementedError(msg)
