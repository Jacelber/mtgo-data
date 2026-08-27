(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.P8ReviewData = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const WILSON_Z = 1.96;
  const MULTI_EVENT_SCHEMA_VERSION = "1.0.0";
  const MULTI_EVENT_LOW_SAMPLE_THRESHOLD = 20;
  const SUPPORTED_MULTI_EVENT_MATCHUP_SCHEMAS = new Set(["1.0.0"]);
  const SUPPORTED_MULTI_EVENT_CATALOG_SCHEMAS = new Set(["1.2.0"]);
  const SUPPORTED_MULTI_EVENT_COMPATIBILITY_SCHEMAS = new Set(["1.0.0"]);
  const SUPPORTED_ACTIVE_TAXONOMY_SCHEMAS = new Set(["1.0.0"]);
  const MULTI_EVENT_ERROR_CODES = Object.freeze([
    "active_taxonomy_mismatch",
    "blocking_quality",
    "catalog_compatibility_mismatch",
    "catalog_event_missing",
    "catalog_identity_mismatch",
    "duplicate_catalog_event",
    "duplicate_event_conflict",
    "event_identity_mismatch",
    "format_mismatch",
    "identity_metadata_mismatch",
    "invalid_contract_input",
    "invalid_event_input",
    "matrix_invariant_failed",
    "missing_active_taxonomy",
    "missing_all_constructed_scope",
    "missing_catalog_compatibility",
    "product_mismatch",
    "provenance_mismatch",
    "source_mismatch",
    "taxonomy_digest_mismatch",
    "taxonomy_version_mismatch",
    "too_few_events",
    "unsupported_catalog_schema",
    "unsupported_matchup_schema",
  ]);
  const MULTI_EVENT_ERROR_CODE_SET = new Set(MULTI_EVENT_ERROR_CODES);
  const COUNT_FIELDS = ["wins", "losses", "draws"];
  const PARENT_MEANING_FIELDS = ["id", "name", "expandable"];
  const LEAF_MEANING_FIELDS = [
    "id", "kind", "name", "display_name", "parent_id", "subtype_id",
  ];

  class MultiEventMatchupError extends Error {
    constructor(code, detail) {
      super(`${code}: ${detail}`);
      this.name = "MultiEventMatchupError";
      this.code = code;
      this.detail = detail;
    }
  }

  function multiEventFail(code, detail) {
    if (!MULTI_EVENT_ERROR_CODE_SET.has(code)) {
      throw new Error(`unregistered multi-event error code: ${code}`);
    }
    throw new MultiEventMatchupError(code, detail);
  }

  function isObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
  }

  function multiEventObject(value, code, detail) {
    if (!isObject(value)) multiEventFail(code, detail);
    return value;
  }

  function sameValue(left, right) {
    if (left === right) return true;
    if (Array.isArray(left) || Array.isArray(right)) {
      return Array.isArray(left)
        && Array.isArray(right)
        && left.length === right.length
        && left.every((item, index) => sameValue(item, right[index]));
    }
    if (!isObject(left) || !isObject(right)) return false;
    const leftKeys = Object.keys(left).sort();
    const rightKeys = Object.keys(right).sort();
    return sameValue(leftKeys, rightKeys)
      && leftKeys.every(key => sameValue(left[key], right[key]));
  }

  function activeMultiEventTaxonomy(catalog) {
    const active = catalog.active_taxonomy;
    if (!isObject(active)) {
      multiEventFail("missing_active_taxonomy", "catalog has no active taxonomy identity");
    }
    if (
      !SUPPORTED_ACTIVE_TAXONOMY_SCHEMAS.has(active.schema_version)
      || typeof active.taxonomy_schema_version !== "string"
      || !active.taxonomy_schema_version
      || typeof active.taxonomy_sha256 !== "string"
      || !/^[0-9a-f]{64}$/.test(active.taxonomy_sha256)
    ) {
      multiEventFail(
        "active_taxonomy_mismatch",
        "catalog active taxonomy identity is invalid or unsupported"
      );
    }
    return active;
  }

  function numericEventOrder(left, right) {
    return Number(left) - Number(right);
  }

  function nonnegativeInteger(value) {
    return Number.isInteger(value) && value >= 0;
  }

  function roundSix(value) {
    return Number(value.toFixed(6));
  }

  function multiEventRecord(counts, contributors, mirror) {
    const matches = counts.wins + counts.losses + counts.draws;
    let interval = null;
    if (matches) {
      const rate = counts.wins / matches;
      const denominator = 1 + (WILSON_Z * WILSON_Z) / matches;
      const center = (rate + (WILSON_Z * WILSON_Z) / (2 * matches)) / denominator;
      const margin = (
        WILSON_Z
        * Math.sqrt(
          (rate * (1 - rate)) / matches
          + (WILSON_Z * WILSON_Z) / (4 * matches * matches)
        )
        / denominator
      );
      interval = {
        lower: roundSix(Math.max(0, center - margin)),
        upper: roundSix(Math.min(1, center + margin)),
      };
    }
    return {
      wins: counts.wins,
      losses: counts.losses,
      draws: counts.draws,
      matches,
      win_rate: matches ? roundSix(counts.wins / matches) : null,
      win_rate_method: "wins_over_valid_matches",
      confidence_interval_95: interval,
      mirror: Boolean(mirror),
      low_sample: matches > 0 && matches < MULTI_EVENT_LOW_SAMPLE_THRESHOLD,
      contributing_event_ids: [...contributors].sort(numericEventOrder),
    };
  }

  function identityIndex(rows, label) {
    if (!Array.isArray(rows)) {
      multiEventFail("identity_metadata_mismatch", `${label} identities are invalid`);
    }
    const indexed = new Map();
    rows.forEach((row, position) => {
      if (!isObject(row) || typeof row.id !== "string" || !row.id) {
        multiEventFail(
          "identity_metadata_mismatch",
          `${label} identity ${position} has no stable ID`
        );
      }
      if (indexed.has(row.id)) {
        multiEventFail("identity_metadata_mismatch", `${label} repeats ${row.id}`);
      }
      indexed.set(row.id, row);
    });
    return indexed;
  }

  function canonicalMultiEventHierarchy(hierarchy) {
    const canonical = multiEventObject(
      hierarchy,
      "identity_metadata_mismatch",
      "canonical hierarchy must be an object"
    );
    const parents = Array.isArray(canonical.parents) ? canonical.parents : null;
    const leaves = Array.isArray(canonical.leaves) ? canonical.leaves : null;
    if (!parents?.length || !leaves?.length) {
      multiEventFail("identity_metadata_mismatch", "canonical hierarchy must not be empty");
    }
    const parentIndex = identityIndex(parents, "canonical parent");
    const leafIndex = identityIndex(leaves, "canonical leaf");
    const parentOrder = [...parentIndex.keys()];
    const leafOrder = [...leafIndex.keys()];
    leafIndex.forEach((leaf, leafId) => {
      if (!parentIndex.has(leaf.parent_id)) {
        multiEventFail(
          "identity_metadata_mismatch",
          `canonical leaf ${leafId} has unknown parent ${leaf.parent_id}`
        );
      }
    });
    parentIndex.forEach((parent, parentId) => {
      const expected = leafOrder.filter(leafId => {
        const leaf = leafIndex.get(leafId);
        return leaf.parent_id === parentId && leaf.kind === "subtype";
      });
      if (!sameValue(parent.subtype_ids, expected)) {
        multiEventFail(
          "identity_metadata_mismatch",
          `canonical parent ${parentId} has inconsistent subtype order`
        );
      }
    });
    return { parentIndex, leafIndex, parentOrder, leafOrder };
  }

  function deduplicateMultiEventInputs(eventInputs) {
    if (!Array.isArray(eventInputs)) {
      multiEventFail("invalid_event_input", "event inputs must be an array");
    }
    const unique = new Map();
    eventInputs.forEach((rawInput, position) => {
      const eventInput = multiEventObject(
        rawInput,
        "invalid_event_input",
        `event input ${position} must be an object`
      );
      const meta = multiEventObject(
        eventInput.meta,
        "invalid_event_input",
        `event input ${position} has no meta`
      );
      const matchup = multiEventObject(
        eventInput.matchup,
        "invalid_event_input",
        `event input ${position} has no matchup`
      );
      const eventId = meta.event_id;
      if (
        typeof eventId !== "string"
        || !/^[1-9][0-9]*$/u.test(eventId)
        || matchup.event_id !== eventId
      ) {
        multiEventFail(
          "event_identity_mismatch",
          "event metadata and matchup document IDs must match"
        );
      }
      if (unique.has(eventId)) {
        const existing = unique.get(eventId);
        if (!sameValue(existing.meta, meta) || !sameValue(existing.matchup, matchup)) {
          multiEventFail(
            "duplicate_event_conflict",
            `event ${eventId} was supplied with conflicting documents`
          );
        }
        return;
      }
      unique.set(eventId, { eventId, meta, matchup, eventInput });
    });
    if (unique.size < 2) {
      multiEventFail("too_few_events", "at least two distinct event IDs are required");
    }
    return [...unique.values()].sort((left, right) => (
      numericEventOrder(left.eventId, right.eventId)
    ));
  }

  function validateMultiEventTaxonomy(meta, matchup, eventId) {
    const metaInput = multiEventObject(
      meta.input,
      "invalid_event_input",
      `event ${eventId} meta.input is invalid`
    );
    const matchupInput = multiEventObject(
      matchup.input,
      "invalid_event_input",
      `event ${eventId} matchup.input is invalid`
    );
    const version = metaInput.taxonomy_schema_version;
    if (typeof version !== "string" || !version || matchupInput.taxonomy_schema_version !== version) {
      multiEventFail(
        "taxonomy_version_mismatch",
        `event ${eventId} has inconsistent taxonomy Schema versions`
      );
    }
    const digest = metaInput.taxonomy_sha256;
    if (
      typeof digest !== "string"
      || !/^[0-9a-f]{64}$/u.test(digest)
      || matchupInput.taxonomy_sha256 !== digest
    ) {
      multiEventFail(
        "taxonomy_digest_mismatch",
        `event ${eventId} has inconsistent taxonomy digests`
      );
    }
    return { version, digest };
  }

  function validateMultiEventIdentitySubset(hierarchy, eventId, canonical) {
    const eventHierarchy = multiEventObject(
      hierarchy,
      "identity_metadata_mismatch",
      `event ${eventId} hierarchy is invalid`
    );
    if (!Array.isArray(eventHierarchy.parents) || !Array.isArray(eventHierarchy.leaves)) {
      multiEventFail("identity_metadata_mismatch", `event ${eventId} hierarchy is invalid`);
    }
    if (!eventHierarchy.parents.length || !eventHierarchy.leaves.length) {
      multiEventFail("identity_metadata_mismatch", `event ${eventId} hierarchy is empty`);
    }
    const parentIndex = identityIndex(eventHierarchy.parents, `event ${eventId} parent`);
    const leafIndex = identityIndex(eventHierarchy.leaves, `event ${eventId} leaf`);
    const parentOrder = [...parentIndex.keys()];
    const leafOrder = [...leafIndex.keys()];
    if (
      parentOrder.some(identityId => !canonical.parentIndex.has(identityId))
      || leafOrder.some(identityId => !canonical.leafIndex.has(identityId))
    ) {
      multiEventFail(
        "identity_metadata_mismatch",
        `event ${eventId} contains an identity outside the canonical hierarchy`
      );
    }
    const leafToParent = new Map();
    leafIndex.forEach((leaf, leafId) => {
      const canonicalLeaf = canonical.leafIndex.get(leafId);
      const meaningChanged = LEAF_MEANING_FIELDS.some(field => (
        !sameValue(leaf[field], canonicalLeaf[field])
      ));
      if (meaningChanged) {
        multiEventFail(
          "identity_metadata_mismatch",
          `event ${eventId} leaf ${leafId} changed stable meaning`
        );
      }
      if (typeof leaf.parent_id !== "string" || !parentIndex.has(leaf.parent_id)) {
        multiEventFail(
          "identity_metadata_mismatch",
          `event ${eventId} leaf ${leafId} has no observed parent`
        );
      }
      leafToParent.set(leafId, leaf.parent_id);
    });
    parentIndex.forEach((parent, parentId) => {
      const canonicalParent = canonical.parentIndex.get(parentId);
      const meaningChanged = PARENT_MEANING_FIELDS.some(field => (
        !sameValue(parent[field], canonicalParent[field])
      ));
      if (meaningChanged) {
        multiEventFail(
          "identity_metadata_mismatch",
          `event ${eventId} parent ${parentId} changed stable meaning`
        );
      }
      const expectedSubtypes = leafOrder.filter(leafId => {
        const leaf = leafIndex.get(leafId);
        return leaf.parent_id === parentId && leaf.kind === "subtype";
      });
      if (!sameValue(parent.subtype_ids, expectedSubtypes)) {
        multiEventFail(
          "identity_metadata_mismatch",
          `event ${eventId} parent ${parentId} has inconsistent subtypes`
        );
      }
    });
    return { parentOrder, leafOrder };
  }

  function validateMultiEventScope(scope, eventId, parentOrder, leafOrder) {
    const eventScope = multiEventObject(
      scope,
      "invalid_event_input",
      `event ${eventId} all_constructed scope is invalid`
    );
    if (
      !sameValue(eventScope.parent_order, parentOrder)
      || !sameValue(eventScope.leaf_order, leafOrder)
    ) {
      multiEventFail(
        "identity_metadata_mismatch",
        `event ${eventId} scope order does not match its hierarchy`
      );
    }
    const rawMatrix = multiEventObject(
      eventScope.leaf_matrix,
      "invalid_event_input",
      `event ${eventId} all_constructed leaf matrix is invalid`
    );
    if (!sameValue(Object.keys(rawMatrix).sort(), [...leafOrder].sort())) {
      multiEventFail(
        "matrix_invariant_failed",
        `event ${eventId} leaf matrix rows do not match leaf order`
      );
    }
    const matrix = {};
    let observations = 0;
    leafOrder.forEach(rowId => {
      const rawColumns = multiEventObject(
        rawMatrix[rowId],
        "invalid_event_input",
        `event ${eventId} matrix row ${rowId} is invalid`
      );
      if (!sameValue(Object.keys(rawColumns).sort(), [...leafOrder].sort())) {
        multiEventFail(
          "matrix_invariant_failed",
          `event ${eventId} matrix row ${rowId} has incomplete columns`
        );
      }
      matrix[rowId] = {};
      leafOrder.forEach(columnId => {
        const rawCell = multiEventObject(
          rawColumns[columnId],
          "invalid_event_input",
          `event ${eventId} matrix cell ${rowId}/${columnId} is invalid`
        );
        if (COUNT_FIELDS.some(field => !nonnegativeInteger(rawCell[field]))) {
          multiEventFail(
            "matrix_invariant_failed",
            `event ${eventId} matrix cell ${rowId}/${columnId} has invalid counts`
          );
        }
        const cell = {
          wins: rawCell.wins,
          losses: rawCell.losses,
          draws: rawCell.draws,
        };
        matrix[rowId][columnId] = cell;
        observations += cell.wins + cell.losses + cell.draws;
      });
    });
    leafOrder.forEach(rowId => {
      leafOrder.forEach(columnId => {
        const cell = matrix[rowId][columnId];
        const inverse = matrix[columnId][rowId];
        if (
          cell.wins !== inverse.losses
          || cell.losses !== inverse.wins
          || cell.draws !== inverse.draws
          || (rowId === columnId && cell.draws % 2 !== 0)
        ) {
          multiEventFail(
            "matrix_invariant_failed",
            `event ${eventId} matrix cell ${rowId}/${columnId} is not inverse`
          );
        }
      });
    });
    const source = eventScope.source_match_count;
    const included = eventScope.included_match_count;
    const excluded = eventScope.excluded_match_count;
    const directed = eventScope.directed_observation_count;
    if (![source, included, excluded, directed].every(nonnegativeInteger)) {
      multiEventFail("matrix_invariant_failed", `event ${eventId} scope counts are invalid`);
    }
    if (directed !== observations || observations !== 2 * included) {
      multiEventFail(
        "matrix_invariant_failed",
        `event ${eventId} directed observations do not conserve physical matches`
      );
    }
    if (source !== included + excluded) {
      multiEventFail(
        "matrix_invariant_failed",
        `event ${eventId} source matches do not reconcile`
      );
    }
    const exclusions = multiEventObject(
      eventScope.excluded_match_counts,
      "invalid_event_input",
      `event ${eventId} exclusion counts are invalid`
    );
    const exclusionEntries = Object.entries(exclusions);
    if (
      !exclusionEntries.length
      || exclusionEntries.some(([key, value]) => !key || !nonnegativeInteger(value))
      || exclusionEntries.reduce((total, [, value]) => total + value, 0) !== excluded
    ) {
      multiEventFail(
        "matrix_invariant_failed",
        `event ${eventId} exclusions do not reconcile`
      );
    }
    return { matrix, source, included, excluded, exclusions };
  }

  function blankMultiEventMatrix(order) {
    return Object.fromEntries(order.map(rowId => [
      rowId,
      Object.fromEntries(order.map(columnId => [columnId, blankRecord()])),
    ]));
  }

  function blankMultiEventContributors(order) {
    return Object.fromEntries(order.map(rowId => [
      rowId,
      Object.fromEntries(order.map(columnId => [columnId, new Set()])),
    ]));
  }

  function emitMultiEventMatrix(matrix, contributors, order) {
    return Object.fromEntries(order.map(rowId => [
      rowId,
      Object.fromEntries(order.map(columnId => [
        columnId,
        multiEventRecord(
          matrix[rowId][columnId],
          contributors[rowId][columnId],
          rowId === columnId
        ),
      ])),
    ]));
  }

  function emitMultiEventOverall(matrix, contributors, order) {
    return Object.fromEntries(order.map(rowId => {
      const counts = blankRecord();
      const eventIds = new Set();
      order.forEach(columnId => {
        if (rowId === columnId) return;
        addRecord(counts, matrix[rowId][columnId]);
        contributors[rowId][columnId].forEach(eventId => eventIds.add(eventId));
      });
      return [rowId, multiEventRecord(counts, eventIds, false)];
    }));
  }

  function aggregateMultiEventMatchups(eventInputs, canonicalHierarchy) {
    const canonical = canonicalMultiEventHierarchy(canonicalHierarchy);
    const inputs = deduplicateMultiEventInputs(eventInputs);
    const validated = [];
    const observedParentIds = new Set();
    const observedLeafIds = new Set();
    let formatId = null;
    let taxonomyVersion = null;
    let taxonomyDigest = null;

    inputs.forEach(({ eventId, meta, matchup }) => {
      if (meta.document_type !== "meta" || matchup.document_type !== "matchup") {
        multiEventFail("invalid_event_input", `event ${eventId} requires meta and matchup`);
      }
      if (meta.source !== "melee" || matchup.source !== "melee") {
        multiEventFail("source_mismatch", `event ${eventId} is not from Melee`);
      }
      if (meta.product !== "tabletop-major-events") {
        multiEventFail("product_mismatch", `event ${eventId} is not a Tabletop input`);
      }
      const eventFormat = meta.format;
      if (typeof eventFormat !== "string" || matchup.format !== eventFormat) {
        multiEventFail("format_mismatch", `event ${eventId} metadata and format differ`);
      }
      if (formatId === null) formatId = eventFormat;
      else if (eventFormat !== formatId) {
        multiEventFail("format_mismatch", "selected events use different formats");
      }
      if (!SUPPORTED_MULTI_EVENT_MATCHUP_SCHEMAS.has(matchup.schema_version)) {
        multiEventFail(
          "unsupported_matchup_schema",
          `event ${eventId} matchup Schema is unsupported`
        );
      }
      const quality = multiEventObject(
        meta.quality,
        "invalid_event_input",
        `event ${eventId} quality is invalid`
      );
      if (
        quality.blocking !== false
        || !["pass", "warning"].includes(quality.status)
      ) {
        multiEventFail("blocking_quality", `event ${eventId} has blocking quality`);
      }
      const scopes = multiEventObject(
        matchup.scopes,
        "invalid_event_input",
        `event ${eventId} scopes are invalid`
      );
      if (
        !Array.isArray(meta.scope_order)
        || !meta.scope_order.includes("all_constructed")
        || !sameValue(matchup.scope_order, meta.scope_order)
        || !Object.hasOwn(scopes, "all_constructed")
      ) {
        multiEventFail(
          "missing_all_constructed_scope",
          `event ${eventId} does not expose all_constructed`
        );
      }
      const taxonomy = validateMultiEventTaxonomy(meta, matchup, eventId);
      if (taxonomyVersion === null) taxonomyVersion = taxonomy.version;
      else if (taxonomy.version !== taxonomyVersion) {
        multiEventFail(
          "taxonomy_version_mismatch",
          "selected events use different taxonomy Schema versions"
        );
      }
      if (taxonomyDigest === null) taxonomyDigest = taxonomy.digest;
      else if (taxonomy.digest !== taxonomyDigest) {
        multiEventFail(
          "taxonomy_digest_mismatch",
          "selected events use different taxonomy digests"
        );
      }
      const metaEvent = multiEventObject(
        meta.event,
        "invalid_event_input",
        `event ${eventId} has no event metadata`
      );
      const matchupEvent = multiEventObject(
        matchup.event,
        "invalid_event_input",
        `event ${eventId} matchup has no event metadata`
      );
      if (
        typeof metaEvent.name !== "string"
        || !metaEvent.name
        || matchupEvent.name !== metaEvent.name
      ) {
        multiEventFail("event_identity_mismatch", `event ${eventId} name differs`);
      }
      const identity = validateMultiEventIdentitySubset(
        matchup.hierarchy,
        eventId,
        canonical
      );
      const scope = validateMultiEventScope(
        scopes.all_constructed,
        eventId,
        identity.parentOrder,
        identity.leafOrder
      );
      identity.parentOrder.forEach(identityId => observedParentIds.add(identityId));
      identity.leafOrder.forEach(identityId => observedLeafIds.add(identityId));
      validated.push({
        eventId,
        eventName: metaEvent.name,
        parentOrder: identity.parentOrder,
        leafOrder: identity.leafOrder,
        schemaVersion: matchup.schema_version,
        ...scope,
      });
    });

    const parentOrder = canonical.parentOrder.filter(id => observedParentIds.has(id));
    const leafOrder = canonical.leafOrder.filter(id => observedLeafIds.has(id));
    const leafToParent = Object.fromEntries(leafOrder.map(leafId => [
      leafId,
      canonical.leafIndex.get(leafId).parent_id,
    ]));
    const leafMatrix = blankMultiEventMatrix(leafOrder);
    const leafContributors = blankMultiEventContributors(leafOrder);
    const excludedMatchCounts = {};
    let sourceMatchCount = 0;
    let includedMatchCount = 0;
    let excludedMatchCount = 0;
    validated.forEach(event => {
      sourceMatchCount += event.source;
      includedMatchCount += event.included;
      excludedMatchCount += event.excluded;
      Object.entries(event.exclusions).forEach(([key, value]) => {
        excludedMatchCounts[key] = (excludedMatchCounts[key] || 0) + value;
      });
      event.leafOrder.forEach(rowId => {
        event.leafOrder.forEach(columnId => {
          const cell = event.matrix[rowId][columnId];
          addRecord(leafMatrix[rowId][columnId], cell);
          if (COUNT_FIELDS.some(field => cell[field])) {
            leafContributors[rowId][columnId].add(event.eventId);
          }
        });
      });
    });
    const observations = leafOrder.reduce((total, rowId) => (
      total + leafOrder.reduce((rowTotal, columnId) => {
        const cell = leafMatrix[rowId][columnId];
        return rowTotal + cell.wins + cell.losses + cell.draws;
      }, 0)
    ), 0);
    if (observations !== 2 * includedMatchCount) {
      multiEventFail(
        "matrix_invariant_failed",
        "combined leaf observations do not conserve physical matches"
      );
    }
    const parentMatrix = blankMultiEventMatrix(parentOrder);
    const parentContributors = blankMultiEventContributors(parentOrder);
    leafOrder.forEach(rowId => {
      leafOrder.forEach(columnId => {
        const parentRow = leafToParent[rowId];
        const parentColumn = leafToParent[columnId];
        addRecord(parentMatrix[parentRow][parentColumn], leafMatrix[rowId][columnId]);
        leafContributors[rowId][columnId].forEach(eventId => {
          parentContributors[parentRow][parentColumn].add(eventId);
        });
      });
    });
    const parentObservations = parentOrder.reduce((total, rowId) => (
      total + parentOrder.reduce((rowTotal, columnId) => {
        const cell = parentMatrix[rowId][columnId];
        return rowTotal + cell.wins + cell.losses + cell.draws;
      }, 0)
    ), 0);
    if (parentObservations !== observations) {
      multiEventFail(
        "matrix_invariant_failed",
        "combined parent roll-up does not reconcile with leaf counts"
      );
    }
    const hierarchy = {
      parents: parentOrder.map(parentId => ({
        ...canonical.parentIndex.get(parentId),
        subtype_ids: leafOrder.filter(leafId => {
          const leaf = canonical.leafIndex.get(leafId);
          return leaf.parent_id === parentId && leaf.kind === "subtype";
        }),
      })),
      leaves: leafOrder.map(leafId => ({ ...canonical.leafIndex.get(leafId) })),
    };
    return {
      document_type: "multi_event_matchup",
      source: "melee",
      product: "tabletop-major-events",
      format: formatId,
      scope: "all_constructed",
      event_ids: validated.map(event => event.eventId),
      event_names: validated.map(event => event.eventName),
      compatibility: {
        matchup_schema_version: validated[0].schemaVersion,
        taxonomy_schema_version: taxonomyVersion,
        taxonomy_sha256: taxonomyDigest,
      },
      rate_method: {
        literal_win_rate_method: "wins_over_valid_matches",
        confidence_interval: "wilson_95",
        low_sample_threshold: MULTI_EVENT_LOW_SAMPLE_THRESHOLD,
      },
      hierarchy,
      source_match_count: sourceMatchCount,
      included_match_count: includedMatchCount,
      excluded_match_count: excludedMatchCount,
      directed_observation_count: observations,
      excluded_match_counts: Object.fromEntries(
        Object.keys(excludedMatchCounts).sort().map(key => [key, excludedMatchCounts[key]])
      ),
      parent_order: parentOrder,
      parent_overall: emitMultiEventOverall(parentMatrix, parentContributors, parentOrder),
      parent_matrix: emitMultiEventMatrix(parentMatrix, parentContributors, parentOrder),
      leaf_order: leafOrder,
      leaf_overall: emitMultiEventOverall(leafMatrix, leafContributors, leafOrder),
      leaf_matrix: emitMultiEventMatrix(leafMatrix, leafContributors, leafOrder),
    };
  }

  function multiEventCatalogIndex(catalog) {
    if (!Array.isArray(catalog.events)) {
      multiEventFail("invalid_contract_input", "catalog events must be an array");
    }
    const events = new Map();
    catalog.events.forEach((rawEvent, position) => {
      const event = multiEventObject(
        rawEvent,
        "invalid_contract_input",
        `catalog event ${position} must be an object`
      );
      if (typeof event.event_id !== "string" || !/^[1-9][0-9]*$/u.test(event.event_id)) {
        multiEventFail("invalid_contract_input", `catalog event ${position} has no valid ID`);
      }
      if (events.has(event.event_id)) {
        multiEventFail("duplicate_catalog_event", `catalog repeats event ${event.event_id}`);
      }
      events.set(event.event_id, event);
    });
    return events;
  }

  function admitMultiEventCatalogEntry(
    eventId,
    eventName,
    eventInput,
    catalogEvent,
    activeTaxonomy,
    formatId
  ) {
    const meta = multiEventObject(
      eventInput.meta,
      "invalid_contract_input",
      `event ${eventId} has no meta`
    );
    const matchup = multiEventObject(
      eventInput.matchup,
      "invalid_contract_input",
      `event ${eventId} has no matchup`
    );
    const metaEvent = multiEventObject(
      meta.event,
      "provenance_mismatch",
      `event ${eventId} has no event metadata`
    );
    const quality = multiEventObject(
      meta.quality,
      "provenance_mismatch",
      `event ${eventId} has no quality metadata`
    );
    const inputDocument = multiEventObject(
      meta.input,
      "provenance_mismatch",
      `event ${eventId} has no taxonomy input`
    );
    const outputs = multiEventObject(
      meta.outputs,
      "provenance_mismatch",
      `event ${eventId} has no output descriptors`
    );
    const descriptor = multiEventObject(
      outputs.matchup,
      "provenance_mismatch",
      `event ${eventId} has no matchup descriptor`
    );
    const compatibility = catalogEvent.matchup_compatibility;
    if (!isObject(compatibility)) {
      multiEventFail(
        "missing_catalog_compatibility",
        `catalog event ${eventId} has no compatibility evidence`
      );
    }
    if (!SUPPORTED_MULTI_EVENT_COMPATIBILITY_SCHEMAS.has(compatibility.schema_version)) {
      multiEventFail(
        "catalog_compatibility_mismatch",
        `catalog event ${eventId} uses unsupported compatibility Schema`
      );
    }
    const expected = {
      schema_version: "1.0.0",
      source: "melee",
      product: "tabletop-major-events",
      format: formatId,
      scope: "all_constructed",
      matchup_schema_version: matchup.schema_version,
      matchup_sha256: descriptor.sha256,
      taxonomy_schema_version: inputDocument.taxonomy_schema_version,
      taxonomy_sha256: inputDocument.taxonomy_sha256,
      quality_blocking: false,
    };
    if (!sameValue(compatibility, expected)) {
      multiEventFail(
        "catalog_compatibility_mismatch",
        `catalog event ${eventId} evidence does not match validated inputs`
      );
    }
    if (
      compatibility.taxonomy_schema_version !== activeTaxonomy.taxonomy_schema_version
      || compatibility.taxonomy_sha256 !== activeTaxonomy.taxonomy_sha256
    ) {
      multiEventFail(
        "active_taxonomy_mismatch",
        `catalog event ${eventId} does not use the active taxonomy`
      );
    }
    const metaPath = `events/${eventId}/meta.json`;
    const matchupPath = `events/${eventId}/matchup.json`;
    const validScopeOrder = sameValue(catalogEvent.scope_order, ["all_constructed"])
      || sameValue(catalogEvent.scope_order, ["day1", "day2", "all_constructed"]);
    if (
      catalogEvent.name !== eventName
      || metaEvent.name !== eventName
      || catalogEvent.meta !== metaPath
      || catalogEvent.matchup !== matchupPath
      || descriptor.path !== "matchup.json"
      || !validScopeOrder
      || catalogEvent.default_scope !== "all_constructed"
      || catalogEvent.quality_status !== quality.status
    ) {
      multiEventFail(
        "provenance_mismatch",
        `catalog event ${eventId} paths or identity do not reconcile`
      );
    }
    return {
      event_id: eventId,
      event_name: eventName,
      meta_path: metaPath,
      matchup_path: matchupPath,
      matchup_schema_version: compatibility.matchup_schema_version,
      matchup_sha256: compatibility.matchup_sha256,
      taxonomy_schema_version: compatibility.taxonomy_schema_version,
      taxonomy_sha256: compatibility.taxonomy_sha256,
    };
  }

  function buildMultiEventMatchupContract(eventInputs, canonicalHierarchy, catalog) {
    if (!Array.isArray(eventInputs)) {
      multiEventFail("invalid_contract_input", "event inputs must be an array");
    }
    const activeCatalog = multiEventObject(
      catalog,
      "invalid_contract_input",
      "catalog must be an object"
    );
    if (!SUPPORTED_MULTI_EVENT_CATALOG_SCHEMAS.has(activeCatalog.schema_version)) {
      multiEventFail(
        "unsupported_catalog_schema",
        `catalog Schema ${activeCatalog.schema_version} is not multi-event eligible`
      );
    }
    const activeTaxonomy = activeMultiEventTaxonomy(activeCatalog);
    const result = aggregateMultiEventMatchups(eventInputs, canonicalHierarchy);
    if (
      activeCatalog.document_type !== "event_catalog"
      || activeCatalog.source !== result.source
      || activeCatalog.product !== result.product
      || activeCatalog.format !== result.format
    ) {
      multiEventFail(
        "catalog_identity_mismatch",
        "catalog source, product, or format does not match selected inputs"
      );
    }
    const catalogEvents = multiEventCatalogIndex(activeCatalog);
    const inputsById = new Map();
    eventInputs.forEach(eventInput => {
      if (isObject(eventInput?.meta) && typeof eventInput.meta.event_id === "string") {
        if (!inputsById.has(eventInput.meta.event_id)) {
          inputsById.set(eventInput.meta.event_id, eventInput);
        }
      }
    });
    const admittedInputs = result.event_ids.map((eventId, index) => {
      if (!catalogEvents.has(eventId)) {
        multiEventFail("catalog_event_missing", `event ${eventId} is not in the catalog`);
      }
      if (!inputsById.has(eventId)) {
        multiEventFail("invalid_contract_input", `event ${eventId} input is unavailable`);
      }
      return admitMultiEventCatalogEntry(
        eventId,
        result.event_names[index],
        inputsById.get(eventId),
        catalogEvents.get(eventId),
        activeTaxonomy,
        result.format
      );
    });
    if (new Set(admittedInputs.map(item => item.matchup_schema_version)).size !== 1) {
      multiEventFail(
        "catalog_compatibility_mismatch",
        "catalog-admitted matchup Schema versions differ"
      );
    }
    return {
      schema_version: MULTI_EVENT_SCHEMA_VERSION,
      ...result,
      inputs: admittedInputs,
      compatibility: {
        catalog_schema_version: activeCatalog.schema_version,
        catalog_compatibility_schema_version: "1.0.0",
        active_taxonomy_schema_version: activeTaxonomy.schema_version,
        ...result.compatibility,
      },
    };
  }

  function blankRecord() {
    return { wins: 0, losses: 0, draws: 0 };
  }

  function addRecord(target, source) {
    if (!source) return;
    target.wins += Number(source.wins) || 0;
    target.losses += Number(source.losses) || 0;
    target.draws += Number(source.draws) || 0;
  }

  function literalRecord(counts, mirror = false, lowSampleThreshold = null) {
    const matches = counts.wins + counts.losses + counts.draws;
    if (!matches) {
      return {
        ...counts,
        matches: 0,
        win_rate: null,
        confidence_interval_95: null,
        low_sample: lowSampleThreshold !== null,
        mirror: Boolean(mirror),
      };
    }
    const rate = counts.wins / matches;
    const denominator = 1 + (WILSON_Z * WILSON_Z) / matches;
    const center = (rate + (WILSON_Z * WILSON_Z) / (2 * matches)) / denominator;
    const half = (
      WILSON_Z
      * Math.sqrt(
        (rate * (1 - rate)) / matches
        + (WILSON_Z * WILSON_Z) / (4 * matches * matches)
      )
      / denominator
    );
    return {
      ...counts,
      matches,
      win_rate: rate,
      confidence_interval_95: {
        lower: Math.max(0, center - half),
        upper: Math.min(1, center + half),
      },
      low_sample: lowSampleThreshold !== null && matches < lowSampleThreshold,
      mirror: Boolean(mirror),
    };
  }

  function activeMatchupDocument(document, lowSampleThreshold) {
    const activeLeaves = new Set();
    Object.entries(document.leaf_matrix || {}).forEach(([rowId, columns]) => {
      Object.entries(columns || {}).forEach(([columnId, cell]) => {
        const record = cell?.literal_record || cell || {};
        const matches = (Number(record.wins) || 0)
          + (Number(record.losses) || 0)
          + (Number(record.draws) || 0);
        if (matches > 0) {
          activeLeaves.add(rowId);
          activeLeaves.add(columnId);
        }
      });
    });
    const parents = (document.hierarchy?.parents || []).map(parent => {
      const subtypeIds = (parent.subtype_ids || []).filter(id => activeLeaves.has(id));
      return {
        ...parent,
        subtype_ids: subtypeIds,
        expandable: subtypeIds.length >= 2,
      };
    });
    const leaves = (document.hierarchy?.leaves || []).filter(leaf => activeLeaves.has(leaf.id));
    const leafMatrix = {};
    activeLeaves.forEach(rowId => {
      leafMatrix[rowId] = {};
      activeLeaves.forEach(columnId => {
        if (document.leaf_matrix?.[rowId]?.[columnId]) {
          leafMatrix[rowId][columnId] = document.leaf_matrix[rowId][columnId];
        }
      });
    });
    return {
      ...document,
      min_sample_hint: lowSampleThreshold,
      hierarchy: { ...document.hierarchy, parents, leaves },
      leaf_matrix: leafMatrix,
    };
  }

  function buildIndexes(document) {
    if (!document || document.hierarchical !== true) {
      throw new Error("需要 hierarchical=true 的对阵数据。");
    }
    const parents = document.hierarchy?.parents || [];
    const leaves = document.hierarchy?.leaves || [];
    const parentById = new Map(parents.map(parent => [parent.id, parent]));
    const leafById = new Map(leaves.map(leaf => [leaf.id, leaf]));
    const leavesByParent = new Map();
    leaves.forEach(leaf => {
      if (!parentById.has(leaf.parent_id)) {
        throw new Error(`未知类型：${leaf.parent_id}`);
      }
      if (!leavesByParent.has(leaf.parent_id)) leavesByParent.set(leaf.parent_id, []);
      leavesByParent.get(leaf.parent_id).push(leaf.id);
    });
    return { parentById, leafById, leavesByParent };
  }

  function normalizeSearch(value) {
    return String(value || "")
      .normalize("NFKC")
      .trim()
      .replace(/\s+/gu, " ")
      .toLocaleLowerCase();
  }

  function mainstreamParentIds(records, identityKey, shareKey, threshold = 0.02) {
    if (!Array.isArray(records)) return null;
    const eligible = new Set();
    let hasComparableShare = false;
    records.forEach(record => {
      const identity = String(record?.[identityKey] || "").trim();
      if (!identity || identity.toLocaleLowerCase() === "unknown") return;
      const rawShare = record?.[shareKey];
      if (rawShare === null || rawShare === undefined || rawShare === "") return;
      const share = Number(rawShare);
      if (!Number.isFinite(share)) return;
      hasComparableShare = true;
      if (share >= threshold) eligible.add(identity);
    });
    return hasComparableShare ? eligible : null;
  }

  function parentNode(parent, parentId) {
    return {
      id: parent.id,
      kind: "archetype",
      name: parent.name,
      parentId,
      parentName: parent.name,
      expandable: Boolean(parent.expandable),
      showAxisToggle: Boolean(parent.expandable),
    };
  }

  function subtypeNode(leaf, parent) {
    return {
      id: leaf.id,
      kind: "subtype",
      name: leaf.display_name || leaf.name,
      parentId: leaf.parent_id,
      parentName: parent.name,
      expandable: false,
      showAxisToggle: false,
    };
  }

  function resolveFilterIdentityFromIndexes(document, indexes, identityId) {
    if (!identityId) return null;
    const parentOrder = new Set(document.parent_order || []);
    const parent = indexes.parentById.get(identityId);
    if (parent && parentOrder.has(parent.id) && (parent.subtype_ids || []).length) {
      return parentNode(parent, parent.id);
    }
    const leaf = indexes.leafById.get(identityId);
    const leafParent = leaf ? indexes.parentById.get(leaf.parent_id) : null;
    return leaf && leafParent && parentOrder.has(leaf.parent_id)
      ? subtypeNode(leaf, leafParent)
      : null;
  }

  function resolveFilterIdentity(document, identityId) {
    return resolveFilterIdentityFromIndexes(document, buildIndexes(document), identityId);
  }

  function filterCandidatesFromIndexes(document, indexes) {
    return (document.parent_order || []).map(parentId => {
      const parent = indexes.parentById.get(parentId);
      if (!parent) throw new Error(`排序中存在未知类型：${parentId}`);
      return {
        ...parentNode(parent, parentId),
        children: (parent.expandable ? parent.subtype_ids || [] : []).map(leafId => {
          const leaf = indexes.leafById.get(leafId);
          if (!leaf) throw new Error(`未知子类型：${leafId}`);
          return subtypeNode(leaf, parent);
        }),
      };
    });
  }

  function filterCandidates(document) {
    return filterCandidatesFromIndexes(document, buildIndexes(document));
  }

  function axisNodes(document, expandedParents, indexes, visibleParentIds = null) {
    const expanded = new Set(expandedParents || []);
    const visibleParents = visibleParentIds === null
      ? null
      : new Set(visibleParentIds || []);
    const nodes = [];
    (document.parent_order || []).forEach(parentId => {
      if (visibleParents !== null && !visibleParents.has(parentId)) return;
      const parent = indexes.parentById.get(parentId);
      if (!parent) throw new Error(`排序中存在未知类型：${parentId}`);
      nodes.push(parentNode(parent, parentId));
      const visibleSubtypeIds = parent.expandable && expanded.has(parentId)
        ? parent.subtype_ids
        : [];
      visibleSubtypeIds.forEach(leafId => {
          const leaf = indexes.leafById.get(leafId);
          if (!leaf) throw new Error(`未知子类型：${leafId}`);
          nodes.push(subtypeNode(leaf, parent));
      });
    });
    return nodes;
  }

  function leavesForNode(node, indexes) {
    if (node.kind === "subtype") return [node.id];
    return indexes.leavesByParent.get(node.parentId) || [];
  }

  function aggregateCell(document, rowNode, columnNode, indexes) {
    const counts = blankRecord();
    const matrix = document.leaf_matrix || {};
    leavesForNode(rowNode, indexes).forEach(rowLeaf => {
      const columns = matrix[rowLeaf] || {};
      leavesForNode(columnNode, indexes).forEach(columnLeaf => {
        addRecord(counts, columns[columnLeaf]);
      });
    });
    return literalRecord(
      counts,
      rowNode.parentId === columnNode.parentId,
      Number.isFinite(document.min_sample_hint) ? document.min_sample_hint : null
    );
  }

  function aggregateOverall(document, rowNode, indexes) {
    const counts = blankRecord();
    const matrix = document.leaf_matrix || {};
    leavesForNode(rowNode, indexes).forEach(rowLeaf => {
      Object.values(matrix[rowLeaf] || {}).forEach(cell => addRecord(counts, cell));
    });
    return literalRecord(
      counts,
      false,
      Number.isFinite(document.min_sample_hint) ? document.min_sample_hint : null
    );
  }

  function buildVisibleView(
    document,
    expandedRows,
    expandedColumns,
    filterIdentities = null,
    visibleParentIds = null
  ) {
    const indexes = buildIndexes(document);
    const selected = filterIdentities === null ? null : new Set(filterIdentities || []);
    const visibleParents = visibleParentIds === null
      ? null
      : new Set(visibleParentIds || []);
    const rowExpansion = new Set(expandedRows || []);
    const rows = selected === null
      ? axisNodes(document, expandedRows, indexes, visibleParents)
      : filterCandidatesFromIndexes(document, indexes).filter(parent => (
        visibleParents === null || visibleParents.has(parent.id)
      )).flatMap(parent => {
        const parentSelected = selected.has(parent.id);
        return [
          ...(parentSelected ? [parentNode(parent, parent.id)] : []),
          ...parent.children.filter(child => (
            selected.has(child.id)
            || (parentSelected && rowExpansion.has(parent.id))
          )),
        ];
      });
    const columns = axisNodes(document, expandedColumns, indexes, visibleParents);
    const matrix = {};
    const overall = {};
    rows.forEach(row => {
      overall[row.id] = aggregateOverall(document, row, indexes);
      matrix[row.id] = {};
      columns.forEach(column => {
        matrix[row.id][column.id] = aggregateCell(document, row, column, indexes);
      });
    });
    const expandableParentIds = (document.parent_order || []).filter(parentId => {
      return Boolean(indexes.parentById.get(parentId)?.expandable);
    });
    return {
      rows,
      columns,
      matrix,
      overall,
      expandableParentIds,
    };
  }

  function buildView(document, expandedRows, expandedColumns) {
    return buildVisibleView(document, expandedRows, expandedColumns);
  }

  function publicPath(path) {
    if (typeof path !== "string" || !path.startsWith("stats/")) {
      throw new Error(`目录中存在不受支持的公开路径：${path}`);
    }
    return `../../../${path}`;
  }

  return {
    activeMatchupDocument,
    buildMultiEventMatchupContract,
    buildView,
    buildVisibleView,
    filterCandidates,
    literalRecord,
    mainstreamParentIds,
    MULTI_EVENT_ERROR_CODES,
    MultiEventMatchupError,
    normalizeSearch,
    publicPath,
    resolveFilterIdentity,
  };
});
