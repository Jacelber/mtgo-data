"""Shared lifecycle rules for complete MTGO calendar weeks."""

from __future__ import annotations

from datetime import date, timedelta


PROVISIONAL_DAYS_AFTER_WEEK = 7


def seal_on(monday: date) -> date:
    """Return the first date on which one complete week is immutable."""

    if monday.weekday() != 0:
        raise ValueError("MTGO week lifecycle requires a Monday")
    return monday + timedelta(days=7 + PROVISIONAL_DAYS_AFTER_WEEK)


def provisional_through(monday: date) -> date:
    return seal_on(monday) - timedelta(days=1)


def is_sealed(monday: date, *, today: date) -> bool:
    return today >= seal_on(monday)


__all__ = [
    "PROVISIONAL_DAYS_AFTER_WEEK",
    "is_sealed",
    "provisional_through",
    "seal_on",
]
