# Historical project records

Files in this directory preserve evidence that is no longer needed in the
live project-status document. They are historical and non-authoritative.

Use the current documents in the order listed by `AGENTS.md` for scope,
statistics, architecture, decisions, task authorization, and workflow rules.
Use historical files only to trace how an earlier state or decision was
recorded.

## Status snapshots

`STATUS-2026-08-04-pre-P11-13.yaml` is a byte-for-byte copy of
`docs/STATUS.yaml` from master commit
`83a54fe0907e1c8775b643295fd9e15327e0daf5`, immediately before P11-13 split
live state from retained history. Its SHA-256 is
`a8166a61b471b5140e4d67105fea02515e2dde3318429cd85fb6841cc0308c66`.

The snapshot retains all earlier phase plans, task results, resolved blockers,
maintenance records, and superseded state. Those values describe the past and
must not be used to authorize work. Current authorization is recorded only in
`docs/STATUS.yaml`.

## Roadmap history

- `ROADMAP-PHASES-0-11.md` preserves completed Phases 0–11, superseded phase
  specifications, and procedures retired from the live roadmap by GOV-11.
- `ROADMAP-PHASE-12-COMPLETED.md` preserves the completed P12-01 through
  P12-09 task specifications and their embedded implementation history.

At task completion, move detailed completed roadmap material into the matching
phase history file in the same accepted task. Keep only remaining work,
acceptance criteria, and a compact history pointer in `docs/ROADMAP.md`.
