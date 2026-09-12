# Historical project records

Files in this directory preserve evidence that is no longer needed in the
live project-status document. They are historical and non-authoritative.

Use `AGENTS.md` to find the current rule for the question at hand. Historical
files only explain earlier business states and decisions. Their old approval,
test, and operating instructions are retired and are not current procedures.

## Status snapshots

`STATUS-2026-08-04-pre-P11-13.yaml` is a byte-for-byte copy of
`docs/STATUS.yaml` from master commit
`83a54fe0907e1c8775b643295fd9e15327e0daf5`, immediately before P11-13 split
live state from retained history. Its SHA-256 is
`a8166a61b471b5140e4d67105fea02515e2dde3318429cd85fb6841cc0308c66`.

The snapshot retains all earlier phase plans, task results, resolved blockers,
maintenance records, and superseded state. Those values describe the past and
must not be used to authorize work. Current Owner instructions and the confirmed
task plan supply authorization under GOVERNANCE; STATUS records facts.

## Roadmap history

- `ROADMAP-PHASES-0-11.md` preserves completed Phases 0–11 and superseded phase
  specifications.
- `ROADMAP-PHASE-12-COMPLETED.md` preserves the complete Phase 12 task
  sequence, acceptance criteria, closeout evidence, and the embedded
  implementation history accumulated before the phase closed on 2026-08-25.
- `ROADMAP-PHASE-13-COMPLETED.md` preserves the complete Phase 13 design, task
  sequence, acceptance criteria, and cloud closeout evidence through P13-07.
- `ROADMAP-PRE-14-COMPLETED.md` preserves the localization reset, minimal
  implementation contract, acceptance boundary, and retained source evidence.

- `ROADMAP-PHASE-14-COMPLETED.md` preserves the complete Phase 14 task sequence,
  acceptance criteria, and coordinated Pauper publication closeout evidence.

At task completion, move detailed completed roadmap material into the matching
phase history file in the same accepted task. Keep only remaining work,
acceptance criteria, and a compact history pointer in `docs/ROADMAP.md`.

Retired governance-only records are available in Git history, not retained as
another set of working instructions here.
