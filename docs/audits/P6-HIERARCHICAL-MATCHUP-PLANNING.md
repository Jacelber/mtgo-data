# Phase 6 hierarchical matchup planning audit

Date: 2026-07-23
Base production commit: `168e929`
Status: local planning complete; implementation not authorized

## Purpose

Confirm whether the current classifier can produce a classified parent
archetype without a selected subtype, determine whether that state requires a
residual statistical bucket, and preserve the approved backend-to-frontend
development order.

## Rule and event evidence

The read-only scan used the active Standard and Modern rule files and every
exact-format event document present at the base commit.

| Format | Parents | Parents with subtypes | Parents without subtypes | Parents with exactly one subtype | Classified decks | Selected subtype | Classified with null subtype |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 74 | 2 | 72 | 0 | 3,955 | 46 | 3,909 |
| Modern | 55 | 17 | 38 | 0 | 5,726 | 2,360 | 3,366 |

These event-snapshot counts intentionally differ from the frozen P6-03 corpus
because later production updates added Modern event records. The rule-topology
and null-subtype conclusions use the active rules and remain unchanged.

Every classified null subtype belongs to a parent that defines no subtypes.
Neither format contains a classified deck under a subtype-defining parent
without one of that parent's subtypes selected.

Examples of valid null-subtype results include:

- Standard `Izzet Prowess`, selected by rule `izzet-prowess-primary`;
- Standard `Selesnya Offense`, selected by rule
  `selesnya-offense-primary`;
- Modern `Boros Energy`, selected by rule `boros-energy-primary`;
- Modern `Affinity`, selected by rule `affinity-primary`;
- Modern `Amulet Titan`, including the rule `amulet-titan-spelunking`.

Those parents have no maintained subtype definitions. Their null subtype is not
an unclassified residual; the parent is the complete statistical identity.

The Standard parents with subtypes are `4-Color Control` and `Izzet Aggro`,
each with two definitions. Modern has 17 subtype-defining parents, and each has
between two and five definitions. The requested one-subtype suppression rule is
therefore a future-safe presentation rule and does not currently hide an
existing expandable parent.

## Planning conclusion

Do not add an `Other` or `Unspecified` statistical bucket for current data.
Treat parents without subtype definitions as non-expandable complete nodes.
Until the owner resolves OPEN-005, fail visibly if a future classified deck has
a null subtype under a parent that defines subtypes.

Implement the canonical subtype-aware W-L-D calculation in P6-06, before the
front end. Apply the same calculation to Standard in P6-09 and require its
collapsed parent matrix to match the legacy Standard result before enabling the
shared expandable interface.
