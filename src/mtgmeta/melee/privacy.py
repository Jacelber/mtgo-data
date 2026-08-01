"""Privacy boundary for future Melee snapshot persistence.

Source responses are parsed in memory and converted to a small, explicit
resource contract before any response body is written to disk. Participant
references are event-scoped HMAC values so they remain joinable inside one
event without exposing enumerable source identifiers or enabling cross-event
linkage.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import hmac
import json
import re
from typing import Any, Mapping

from .parser import ParsedSourcePage, SourceArtifact, parse_source_response
from .privacy_validation import (
    MeleeResourceValidationError,
    validate_minimized_resource,
)


MINIMIZED_RESOURCE_SCHEMA_VERSION = "1.0.0"
PARTICIPANT_IDENTITY_SCHEME = "hmac-sha256-event-v1"
PARTICIPANT_REF_PATTERN = re.compile(r"^melee-v3-[0-9a-f]{64}$")
KEY_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
MINIMUM_HMAC_KEY_BYTES = 32


class MeleePrivacyError(ValueError):
    """Raised when source material cannot cross the persistence boundary."""


@dataclass(frozen=True)
class ParticipantPseudonymizer:
    event_id: str
    key: bytes
    key_id: str

    def __post_init__(self) -> None:
        if not self.event_id.isdigit() or self.event_id.startswith("0"):
            raise MeleePrivacyError("participant HMAC event ID must be a positive integer string")
        if not isinstance(self.key, bytes) or len(self.key) < MINIMUM_HMAC_KEY_BYTES:
            raise MeleePrivacyError(
                f"participant HMAC key must contain at least {MINIMUM_HMAC_KEY_BYTES} bytes"
            )
        if not isinstance(self.key_id, str) or not KEY_ID_PATTERN.fullmatch(self.key_id):
            raise MeleePrivacyError("participant HMAC key ID has an invalid format")

    def reference(self, source_participant_id: str) -> str:
        if (
            not isinstance(source_participant_id, str)
            or not source_participant_id.isdigit()
            or source_participant_id.startswith("0")
        ):
            raise MeleePrivacyError("source participant ID must be a positive integer string")
        message = (
            f"melee\0v3\0{self.event_id}\0participant\0{source_participant_id}"
        ).encode("utf-8")
        return "melee-v3-" + hmac.new(self.key, message, hashlib.sha256).hexdigest()


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


def _participant_ref(
    pseudonymizer: ParticipantPseudonymizer,
    source_participant_id: str,
) -> str:
    return pseudonymizer.reference(source_participant_id)


def _document(
    page: ParsedSourcePage,
    pseudonymizer: ParticipantPseudonymizer,
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
                "participant_ref": _participant_ref(
                    pseudonymizer, item.source_participant_id
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
                "participant_ref": _participant_ref(
                    pseudonymizer, item.source_participant_id
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
                        "participant_ref": _participant_ref(
                            pseudonymizer, competitor.source_participant_id
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
        if artifact.participant_ref is None or not PARTICIPANT_REF_PATTERN.fullmatch(
            artifact.participant_ref
        ):
            raise MeleePrivacyError("decklist response lacks a valid participant reference")
        base["decklists"] = [
            {
                "source_decklist_id": item.source_decklist_id,
                "participant_ref": artifact.participant_ref,
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
    pseudonymizer: ParticipantPseudonymizer,
) -> MinimizedResponse:
    """Parse one source response in memory and return only approved v3 fields."""

    parsing_artifact = artifact
    if artifact.resource_type == "decklist" and artifact.participant_ref is not None:
        parsing_artifact = replace(
            artifact,
            source_participant_id=artifact.participant_ref,
        )
    page = parse_source_response(body, parsing_artifact)
    if page.tournament is not None and page.tournament.source_event_id != pseudonymizer.event_id:
        raise MeleePrivacyError("tournament response event identity changed")
    records_total = _records_total(body, artifact.resource_type)
    document = _document(page, pseudonymizer, records_total)
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
    "KEY_ID_PATTERN",
    "MINIMIZED_RESOURCE_SCHEMA_VERSION",
    "MINIMUM_HMAC_KEY_BYTES",
    "MeleePrivacyError",
    "MinimizedResponse",
    "PARTICIPANT_IDENTITY_SCHEME",
    "PARTICIPANT_REF_PATTERN",
    "ParticipantPseudonymizer",
    "minimize_source_response",
]
