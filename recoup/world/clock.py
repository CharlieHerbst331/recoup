"""Persistent simulated clock (design/02 §4.4)."""

import sqlite3
from datetime import date, datetime, time, timedelta, timezone


class SimClock:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def day(self) -> int:
        row = self.connection.execute("SELECT value FROM meta WHERE key='sim_day'").fetchone()
        return int(row[0]) if row else 0

    def start_date(self) -> date:
        row = self.connection.execute("SELECT value FROM meta WHERE key='start_date'").fetchone()
        return date.fromisoformat(row[0]) if row else date(2026, 10, 20)

    def at_day(self, day: int) -> datetime:
        return datetime.combine(self.start_date(), time(), timezone.utc) + timedelta(days=day)

    def now(self) -> datetime:
        return self.at_day(self.day())
