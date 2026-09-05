"""Validated explicit format/week scopes for private MTGO review operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

from mtgmeta.config import FormatConfigError, load_format_registry


class MTGOReviewScopeError(ValueError):
    """Raised when an explicit review scope is invalid or unauthorized."""


@dataclass(frozen=True)
class ReviewScope:
    format_id: str
    week: str
    monday: date


def parse_iso_week(value: str) -> date:
    """Return the Monday for a real canonical ISO week label."""

    try:
        monday = datetime.strptime(f"{value}-1", "%G-W%V-%u").date()
    except (TypeError, ValueError) as exc:
        raise MTGOReviewScopeError(f"invalid ISO review week: {value!r}") from exc
    year, week, _weekday = monday.isocalendar()
    if value != f"{year}-W{week:02d}":
        raise MTGOReviewScopeError(f"invalid ISO review week: {value!r}")
    return monday


def parse_review_scopes(
    repository_root: str | Path,
    values: Iterable[str],
    *,
    capability: str,
    registry_path: str | Path | None = None,
    private: bool,
    today: date | None = None,
) -> tuple[ReviewScope, ...]:
    """Validate ordered ``format=week`` scopes against the format registry."""

    root = Path(repository_root).resolve()
    registry = load_format_registry(
        registry_path if registry_path is not None else root / "configs/formats.yaml"
    )
    scopes: list[ReviewScope] = []
    seen: set[str] = set()
    closed_before = (today or date.today()) - timedelta(days=(today or date.today()).weekday())
    for raw in values:
        if not isinstance(raw, str) or raw.count("=") != 1:
            raise MTGOReviewScopeError(
                f"review scope must use <format>=<week>: {raw!r}"
            )
        format_id, week = (part.strip() for part in raw.split("=", 1))
        if not format_id or not week:
            raise MTGOReviewScopeError(
                f"review scope must use <format>=<week>: {raw!r}"
            )
        if format_id in seen:
            raise MTGOReviewScopeError(f"review scope duplicates format {format_id!r}")
        try:
            definition = registry.require_mtgo(format_id)
        except FormatConfigError as exc:
            raise MTGOReviewScopeError(str(exc)) from exc
        if capability not in definition.mtgo.capabilities:
            raise MTGOReviewScopeError(
                f"MTGO format {format_id!r} does not support {capability!r}"
            )
        if private:
            if definition.public:
                raise MTGOReviewScopeError(
                    f"explicit private scope requires public: false for {format_id!r}"
                )
        elif not definition.public:
            raise MTGOReviewScopeError(
                f"default public scope cannot include private format {format_id!r}"
            )
        monday = parse_iso_week(week)
        if monday >= closed_before:
            raise MTGOReviewScopeError(f"review week has not ended: {week}")
        seen.add(format_id)
        scopes.append(ReviewScope(format_id, week, monday))
    if not scopes:
        raise MTGOReviewScopeError("review scope must not be empty")
    return tuple(scopes)


__all__ = ["MTGOReviewScopeError", "ReviewScope", "parse_iso_week", "parse_review_scopes"]
