"""Deterministic cross-resource assembly for parsed Melee snapshots.

P5-05 links the source records emitted by :mod:`mtgmeta.melee.parser` into
one schema-shaped event document.  It intentionally leaves round and result
semantics unresolved for P5-06 and therefore always emits a blocked,
non-publishable document.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable, Iterable, TypeVar

from . import NORMALIZED_EVENT_SCHEMA_VERSION
from .config import MeleeEventDefinition
from .parser import (
    ParsedMeleeSnapshot,
    SourceDecklist,
    SourceDecklistReference,
    SourceMatch,
    SourceRound,
    SourceStanding,
    SourceTournament,
    parse_raw_snapshot,
)


class MeleeAssemblyError(ValueError):
    """Raised when parsed source records cannot be joined unambiguously."""


T = TypeVar("T")


def stable_record_id(kind: str, event_id: str, source_id: str) -> str:
    payload = f"melee\0{event_id}\0{kind}\0{source_id}".encode("utf-8")
    return f"{kind}-{sha256(payload).hexdigest()}"


def _require_normalized_at(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MeleeAssemblyError("normalized_at must be a non-empty ISO-8601 date-time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MeleeAssemblyError("normalized_at must be a valid ISO-8601 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise MeleeAssemblyError("normalized_at must include a UTC offset")
    return value


def _collect_unique(
    records: Iterable[T],
    identity: Callable[[T], str],
    label: str,
) -> dict[str, T]:
    collected: dict[str, T] = {}
    for record in records:
        source_id = identity(record)
        previous = collected.get(source_id)
        if previous is not None and previous != record:
            raise MeleeAssemblyError(f"conflicting {label} records for source ID {source_id!r}")
        collected[source_id] = record
    return collected


def _records(snapshot: ParsedMeleeSnapshot, attribute: str) -> Iterable[Any]:
    for page in snapshot.pages:
        yield from getattr(page, attribute)


def _tournament(snapshot: ParsedMeleeSnapshot) -> SourceTournament:
    tournaments = [page.tournament for page in snapshot.pages if page.tournament is not None]
    if not tournaments:
        raise MeleeAssemblyError("snapshot does not contain a tournament record")
    if any(record != tournaments[0] for record in tournaments[1:]):
        raise MeleeAssemblyError("snapshot contains conflicting tournament records")
    return tournaments[0]


def _source_evidence(*values: str | None) -> list[str]:
    return [value for value in values if value]


def _card_section(source_text: str) -> str:
    normalized = " ".join(source_text.casefold().split())
    return {
        "main": "main",
        "main deck": "main",
        "maindeck": "main",
        "side": "sideboard",
        "sideboard": "sideboard",
        "commander": "commander",
    }.get(normalized, "other")


def _configured_phases(event: MeleeEventDefinition) -> list[dict[str, Any]]:
    if any(phase.id == "unresolved" for phase in event.phases):
        raise MeleeAssemblyError("whitelist phase ID 'unresolved' is reserved for P5-05 assembly")
    phases = [
        {
            "id": phase.id,
            "stage": phase.stage,
            "round_phase": phase.round_phase,
            "game_format": phase.game_format,
            "swiss": phase.swiss,
        }
        for phase in event.phases
    ]
    phases.append(
        {
            "id": "unresolved",
            "stage": "other",
            "round_phase": "unknown",
            "game_format": "unknown",
            "swiss": False,
        }
    )
    return phases


def assemble_parsed_snapshot(
    snapshot: ParsedMeleeSnapshot,
    event: MeleeEventDefinition,
    *,
    normalized_at: str,
) -> dict[str, Any]:
    """Join a parsed snapshot into a deterministic, non-publishable event.

    The caller injects ``normalized_at`` so repeated assembly is reproducible.
    P5-06 must replace unresolved round and result semantics before publication.
    """

    normalized_at = _require_normalized_at(normalized_at)
    if snapshot.event_id != event.id:
        raise MeleeAssemblyError("snapshot event ID does not match the whitelist event")
    if snapshot.event_url != event.url:
        raise MeleeAssemblyError("snapshot event URL does not match the whitelist event")
    tournament = _tournament(snapshot)
    if tournament.source_event_id != event.id:
        raise MeleeAssemblyError("source tournament ID does not match the whitelist event")

    standings = _collect_unique(
        _records(snapshot, "standings"),
        lambda record: record.source_standing_id,
        "standing",
    )
    rounds = _collect_unique(
        _records(snapshot, "rounds"),
        lambda record: record.source_round_id,
        "round",
    )
    if not rounds:
        raise MeleeAssemblyError("snapshot does not contain round records")
    matches = _collect_unique(
        _records(snapshot, "matches"),
        lambda record: record.source_match_id,
        "match",
    )
    references = _collect_unique(
        _records(snapshot, "decklist_references"),
        lambda record: record.source_decklist_id,
        "decklist reference",
    )
    decklists = _collect_unique(
        _records(snapshot, "decklists"),
        lambda record: record.source_decklist_id,
        "decklist",
    )

    standings_by_participant: dict[str, SourceStanding] = {}
    for standing in standings.values():
        previous = standings_by_participant.get(standing.source_participant_id)
        if previous is not None and previous != standing:
            raise MeleeAssemblyError(
                f"multiple standings records for participant {standing.source_participant_id!r}"
            )
        standings_by_participant[standing.source_participant_id] = standing
    if not standings_by_participant:
        raise MeleeAssemblyError("snapshot does not contain standings participants")

    participant_ids = {
        source_id: stable_record_id("participant", event.id, source_id)
        for source_id in standings_by_participant
    }
    if len(set(participant_ids.values())) != len(participant_ids):
        raise MeleeAssemblyError("stable participant ID collision")

    for match in matches.values():
        if match.source_round_id not in rounds:
            raise MeleeAssemblyError(
                f"match {match.source_match_id!r} references unknown round {match.source_round_id!r}"
            )
        missing = [value for value in match.competitor_source_ids if value not in participant_ids]
        if missing:
            raise MeleeAssemblyError(
                f"match {match.source_match_id!r} references unknown participants {missing!r}"
            )

    references_by_participant: dict[str, SourceDecklistReference] = {}
    for reference in references.values():
        if reference.source_participant_id not in participant_ids:
            raise MeleeAssemblyError(
                f"decklist reference {reference.source_decklist_id!r} has an unknown participant"
            )
        previous = references_by_participant.get(reference.source_participant_id)
        if previous is not None and previous != reference:
            raise MeleeAssemblyError(
                f"multiple decklist references for participant {reference.source_participant_id!r}"
            )
        references_by_participant[reference.source_participant_id] = reference

    decklists_by_participant: dict[str, SourceDecklist] = {}
    for decklist in decklists.values():
        if decklist.source_participant_id not in participant_ids:
            raise MeleeAssemblyError(
                f"decklist {decklist.source_decklist_id!r} has an unknown participant"
            )
        reference = references.get(decklist.source_decklist_id)
        if reference is None:
            raise MeleeAssemblyError(
                f"decklist {decklist.source_decklist_id!r} has no source reference"
            )
        if reference.source_participant_id != decklist.source_participant_id:
            raise MeleeAssemblyError(
                f"decklist {decklist.source_decklist_id!r} participant conflicts with its reference"
            )
        previous = decklists_by_participant.get(decklist.source_participant_id)
        if previous is not None and previous != decklist:
            raise MeleeAssemblyError(
                f"multiple decklists for participant {decklist.source_participant_id!r}"
            )
        decklists_by_participant[decklist.source_participant_id] = decklist

    normalized_round_ids = {
        source_id: stable_record_id("round", event.id, source_id) for source_id in rounds
    }
    normalized_match_ids = {
        source_id: stable_record_id("match", event.id, source_id) for source_id in matches
    }
    if len(set(normalized_round_ids.values())) != len(normalized_round_ids):
        raise MeleeAssemblyError("stable round ID collision")
    if len(set(normalized_match_ids.values())) != len(normalized_match_ids):
        raise MeleeAssemblyError("stable match ID collision")

    participant_documents = [
        {
            "id": participant_ids[source_id],
            "source_id": source_id,
            "display_name": standing.display_name,
            "status": "unknown",
        }
        for source_id, standing in sorted(standings_by_participant.items())
    ]
    standing_documents = [
        {
            "participant_id": participant_ids[source_id],
            "rank": standing.rank,
            "match_points": standing.match_points,
            "source_record": asdict(standing),
        }
        for source_id, standing in sorted(standings_by_participant.items())
    ]

    decklist_documents: list[dict[str, Any]] = []
    for source_id in sorted(participant_ids):
        reference = references_by_participant.get(source_id)
        decklist = decklists_by_participant.get(source_id)
        if decklist is not None:
            cards = sorted(
                (
                    {
                        "name": card.name,
                        "quantity": card.quantity,
                        "section": _card_section(card.section_text),
                    }
                    for card in decklist.cards
                ),
                key=lambda card: (card["section"], card["name"].casefold(), card["quantity"]),
            )
            status = "submitted"
        else:
            cards = []
            status = "unavailable" if reference is not None else "missing"
        decklist_documents.append(
            {
                "participant_id": participant_ids[source_id],
                "game_format": "unknown",
                "status": status,
                "cards": cards,
                "source_url": reference.url if reference is not None else None,
            }
        )

    round_documents = [
        {
            "id": normalized_round_ids[source_id],
            "source_label": round_.label,
            "number": round_.number,
            "phase_id": "unresolved",
            "stage": "other",
            "round_phase": "unknown",
            "game_format": "unknown",
            "swiss": False,
        }
        for source_id, round_ in sorted(rounds.items())
    ]
    match_documents = [
        {
            "id": normalized_match_ids[source_id],
            "round_id": normalized_round_ids[match.source_round_id],
            "source_record_id": match.source_match_id,
            "original_result": match.result_text or match.status_text or "",
            "competitors": [
                {
                    "participant_id": participant_ids[competitor],
                    "result_type": "unknown",
                    "match_points": 0,
                }
                for competitor in match.competitor_source_ids
            ],
            "played": False,
            "constructed_statistics_eligible": False,
            "matchup_eligible": False,
            "evidence": _source_evidence(
                f"source_match_id={match.source_match_id}",
                f"source_round_id={match.source_round_id}",
                f"result_text={match.result_text}" if match.result_text else None,
                f"status_text={match.status_text}" if match.status_text else None,
                f"table_number={match.table_number}" if match.table_number is not None else None,
            ),
        }
        for source_id, match in sorted(matches.items())
    ]

    issues = [
        {
            "code": "unknown_round_phase",
            "severity": "error",
            "entity_type": "round",
            "entity_id": normalized_round_ids[source_id],
            "message": "Round semantics are unresolved until P5-06.",
            "blocking": True,
            "source_evidence": [f"source_round_id={source_id}", f"source_label={round_.label}"],
        }
        for source_id, round_ in sorted(rounds.items())
    ]
    issues.extend(
        {
            "code": "unknown_result",
            "severity": "error",
            "entity_type": "match",
            "entity_id": normalized_match_ids[source_id],
            "message": "Match result semantics are unresolved until P5-06.",
            "blocking": True,
            "source_evidence": _source_evidence(
                f"source_match_id={source_id}",
                f"result_text={match.result_text}" if match.result_text else None,
                f"status_text={match.status_text}" if match.status_text else None,
            ),
        }
        for source_id, match in sorted(matches.items())
    )

    secondary_urls = set(event.source_evidence)
    secondary_urls.update(page.artifact.url for page in snapshot.pages)
    secondary_urls.discard(event.url)
    source_urls = [event.url, *sorted(secondary_urls)]
    raw_artifacts = [
        {
            "path": f"data_raw/melee/{event.id}/{page.artifact.path}",
            "source_url": page.artifact.url,
            "sha256": page.artifact.sha256,
        }
        for page in sorted(snapshot.pages, key=lambda page: page.artifact.path)
    ]

    return {
        "schema_version": NORMALIZED_EVENT_SCHEMA_VERSION,
        "metadata": {
            "source": "melee",
            "event_id": event.id,
            "name": event.name,
            "date": {"start": event.start_date.isoformat(), "end": event.end_date.isoformat()},
            "constructed_format": event.format,
            "series": event.series,
        },
        "provenance": {
            "source_urls": source_urls,
            "fetched_at": snapshot.fetched_at,
            "normalized_at": normalized_at,
            "raw_artifacts": raw_artifacts,
        },
        "event_structure": event.structure,
        "phases": _configured_phases(event),
        "rounds": round_documents,
        "participants": participant_documents,
        "standings": standing_documents,
        "decklists": decklist_documents,
        "matches": match_documents,
        "quality": {"status": "blocked", "publishable": False, "issues": issues},
    }


def assemble_raw_snapshot(
    snapshot_path: str | Path,
    event: MeleeEventDefinition,
    *,
    normalized_at: str,
) -> dict[str, Any]:
    """Parse and assemble one stored raw snapshot without network access."""

    return assemble_parsed_snapshot(
        parse_raw_snapshot(snapshot_path),
        event,
        normalized_at=normalized_at,
    )


__all__ = [
    "MeleeAssemblyError",
    "assemble_parsed_snapshot",
    "assemble_raw_snapshot",
    "stable_record_id",
]
