"""Minimization boundary for Melee snapshot persistence.

Source responses are parsed in memory and converted to a small, explicit
resource contract before any response body is written to disk. Public Melee
participant IDs are retained verbatim as stable source identifiers; account
and profile fields outside the approved contract remain prohibited.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

from .parser import ParsedSourcePage, SourceArtifact, parse_source_response
from .privacy_validation import (
    MeleeResourceValidationError,
    validate_minimized_resource,
)


MINIMIZED_RESOURCE_SCHEMA_VERSION = "2.0.0"
PARTICIPANT_IDENTITY_SCHEME = "source-participant-id-v1"


class MeleePrivacyError(ValueError):
    """Raised when source material cannot cross the persistence boundary."""


@dataclass(frozen=True)
class MinimizedResponse:
    body: bytes
    records_total: int | None
    page: ParsedSourcePage


def _optional_fields(**values: Any) -> dict[str, Any]:
    return {key: value for key, value in values.items() if value is not None}


def _records_total(body: bytes, resource_type: str) -> int | None:
    if resource_type not in {"standings", "matches"}:
        return None
    try:
        payload = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MeleePrivacyError(f"{resource_type} response has invalid pagination JSON") from exc
    if not isinstance(payload, Mapping):
        raise MeleePrivacyError(f"{resource_type} response must be a mapping")
    value = payload.get("recordsTotal")
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise MeleePrivacyError(f"{resource_type} response has invalid recordsTotal")
    return value


def _source_participant_id(value: str) -> str:
    if not isinstance(value, str) or not value.isdigit() or value.startswith("0"):
        raise MeleePrivacyError("source participant ID must be a positive integer string")
    return value


def _document(
    page: ParsedSourcePage,
    records_total: int | None,
) -> dict[str, Any]:
    artifact = page.artifact
    base: dict[str, Any] = {
        "schema_version": MINIMIZED_RESOURCE_SCHEMA_VERSION,
        "resource_type": artifact.resource_type,
    }
    if records_total is not None:
        base["records_total"] = records_total
    if artifact.resource_type == "tournament":
        if page.tournament is None:
            raise MeleePrivacyError("tournament response did not produce tournament metadata")
        base["tournament"] = {
            "source_event_id": page.tournament.source_event_id,
            "name": page.tournament.name,
            **_optional_fields(
                start_text=page.tournament.start_text,
                end_text=page.tournament.end_text,
            ),
        }
        base["rounds"] = [
            {
                "source_round_id": item.source_round_id,
                "label": item.label,
                **_optional_fields(number=item.number),
            }
            for item in page.rounds
        ]
    elif artifact.resource_type == "standings":
        base["standings"] = [
            {
                "source_standing_id": item.source_standing_id,
                "source_participant_id": _source_participant_id(
                    item.source_participant_id
                ),
                "display_name": item.display_name,
                **_optional_fields(
                    rank=item.rank,
                    match_points=item.match_points,
                    record_text=item.record_text,
                    status_text=item.status_text,
                ),
            }
            for item in page.standings
        ]
        base["decklist_references"] = [
            {
                "source_decklist_id": item.source_decklist_id,
                "source_participant_id": _source_participant_id(
                    item.source_participant_id
                ),
                "url": item.url,
            }
            for item in page.decklist_references
        ]
    elif artifact.resource_type == "matches":
        base["matches"] = [
            {
                "source_match_id": item.source_match_id,
                "source_round_id": item.source_round_id,
                "competitors": [
                    {
                        "source_participant_id": _source_participant_id(
                            competitor.source_participant_id
                        ),
                        **_optional_fields(
                            outcome_text=competitor.outcome_text,
                            match_points=competitor.match_points,
                        ),
                    }
                    for competitor in item.competitor_results
                ],
                **_optional_fields(
                    result_text=item.result_text,
                    status_text=item.status_text,
                    table_number=item.table_number,
                ),
            }
            for item in page.matches
        ]
    elif artifact.resource_type == "decklist":
        if artifact.source_participant_id is None:
            raise MeleePrivacyError("decklist response lacks a source participant ID")
        source_participant_id = _source_participant_id(artifact.source_participant_id)
        base["decklists"] = [
            {
                "source_decklist_id": item.source_decklist_id,
                "source_participant_id": source_participant_id,
                **_optional_fields(format_text=item.format_text),
                "cards": [
                    {
                        "name": card.name,
                        "quantity": card.quantity,
                        "section_text": card.section_text,
                    }
                    for card in item.cards
                ],
            }
            for item in page.decklists
        ]
    else:  # pragma: no cover - parse_source_response rejects this first
        raise MeleePrivacyError(f"unsupported resource type {artifact.resource_type!r}")
    return base


def minimize_source_response(
    body: bytes,
    artifact: SourceArtifact,
    *,
    event_id: str,
) -> MinimizedResponse:
    """Parse one source response in memory and return only approved v4 fields."""

    if not isinstance(event_id, str) or not event_id.isdigit() or event_id.startswith("0"):
        raise MeleePrivacyError("Melee event ID must be a positive integer string")
    page = parse_source_response(body, artifact)
    if page.tournament is not None and page.tournament.source_event_id != event_id:
        raise MeleePrivacyError("tournament response event identity changed")
    records_total = _records_total(body, artifact.resource_type)
    document = _document(page, records_total)
    try:
        validate_minimized_resource(
            document,
            context=f"{artifact.path} pre-persistence resource",
        )
    except MeleeResourceValidationError as exc:
        raise MeleePrivacyError(str(exc)) from exc
    minimized = (
        json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")
    return MinimizedResponse(minimized, records_total, page)


__all__ = [
    "MINIMIZED_RESOURCE_SCHEMA_VERSION",
    "MeleePrivacyError",
    "MinimizedResponse",
    "PARTICIPANT_IDENTITY_SCHEME",
    "minimize_source_response",
]
