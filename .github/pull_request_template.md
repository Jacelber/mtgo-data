## Task

<!-- Replace REPLACE_ME with every applicable value; keep exactly one marker. -->
<!-- artifact-impact: REPLACE_ME -->

## File operations

Known-path additions need no declaration. Before implementation, copy one exact
marker per unknown-path addition, deletion, or rename from the approved task
contract. Remove `EXAMPLE-` to activate only the operations actually approved.

<!-- EXAMPLE-file-operation: add|docs|review-output/owner-review.md -->
<!-- EXAMPLE-file-operation: delete|docs|docs/obsolete.md -->
<!-- EXAMPLE-file-operation: rename|docs|docs/old.md|docs/history/old.md -->

These markers classify checks only. They do not authorize deletion, public-path
changes, statistical changes, credentials, production, merge, or deployment.

## Owner UI acceptance

For an actual `user_visible_ui` change, complete local browser review on the
final visible files, commit that accepted tree, then replace `EXAMPLE-` below
with the exact marker printed by `.\.venv\Scripts\python.exe -B
ci_master_admission.py --owner-ui-marker-from origin/master`.
Do not activate this marker for test, package, or governance-only changes.

<!-- EXAMPLE-owner-ui-accepted: sha256:0000000000000000000000000000000000000000000000000000000000000000 -->

## Owner review

- Purpose and visible effect:
- Local evidence already obtained:
- Checks intentionally not run:
- Stop point:
