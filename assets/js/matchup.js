(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.MtgMatchup = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const WILSON_Z = 1.96;

  function blankRecord() {
    return { wins: 0, losses: 0, draws: 0 };
  }

  function addRecord(target, source) {
    if (!source) return;
    target.wins += Number(source.wins) || 0;
    target.losses += Number(source.losses) || 0;
    target.draws += Number(source.draws) || 0;
  }

  function emitRecord(record, minSample, mirror) {
    const matches = record.wins + record.losses + record.draws;
    if (!matches) {
      return {
        ...record,
        matches: 0,
        win_rate: null,
        ci_half: null,
        low_sample: true,
        mirror: Boolean(mirror),
      };
    }
    const effectiveWins = record.wins + 0.5 * record.draws;
    const p = effectiveWins / matches;
    const denominator = 1 + (WILSON_Z * WILSON_Z) / matches;
    const ciHalf = (
      WILSON_Z
      * Math.sqrt(
        (p * (1 - p)) / matches
        + (WILSON_Z * WILSON_Z) / (4 * matches * matches)
      )
      / denominator
    );
    return {
      ...record,
      matches,
      win_rate: Number(p.toFixed(4)),
      ci_half: Number(ciHalf.toFixed(4)),
      low_sample: matches < minSample,
      mirror: Boolean(mirror),
    };
  }

  function buildIndexes(document) {
    if (!document || document.hierarchical !== true) {
      throw new Error("Hierarchical matchup data is required.");
    }
    const hierarchy = document.hierarchy || {};
    const parents = Array.isArray(hierarchy.parents) ? hierarchy.parents : [];
    const leaves = Array.isArray(hierarchy.leaves) ? hierarchy.leaves : [];
    const parentById = new Map(parents.map(parent => [parent.id, parent]));
    const leafById = new Map(leaves.map(leaf => [leaf.id, leaf]));
    const leavesByParent = new Map();
    leaves.forEach(leaf => {
      if (!parentById.has(leaf.parent_id)) {
        throw new Error(`Unknown parent identity: ${leaf.parent_id}`);
      }
      if (!leavesByParent.has(leaf.parent_id)) {
        leavesByParent.set(leaf.parent_id, []);
      }
      leavesByParent.get(leaf.parent_id).push(leaf.id);
    });
    return { parentById, leafById, leavesByParent };
  }

  function axisNodes(document, expandedParents, indexes) {
    const expanded = new Set(expandedParents || []);
    const nodes = [];
    (document.parent_order || []).forEach(parentId => {
      const parent = indexes.parentById.get(parentId);
      if (!parent) throw new Error(`Unknown parent order identity: ${parentId}`);
      if (parent.expandable && expanded.has(parentId)) {
        parent.subtype_ids.forEach((leafId, subtypeIndex) => {
          const leaf = indexes.leafById.get(leafId);
          if (!leaf) throw new Error(`Unknown subtype identity: ${leafId}`);
          nodes.push({
            id: leaf.id,
            kind: "subtype",
            name: leaf.name,
            parentId,
            parentName: parent.name,
            expandable: false,
            showAxisToggle: subtypeIndex === 0,
          });
        });
      } else {
        nodes.push({
          id: parent.id,
          kind: "archetype",
          name: parent.name,
          parentId,
          parentName: parent.name,
          expandable: Boolean(parent.expandable),
          showAxisToggle: Boolean(parent.expandable),
        });
      }
    });
    return nodes;
  }

  function leavesForNode(node, indexes) {
    if (node.kind === "subtype") return [node.id];
    return indexes.leavesByParent.get(node.parentId) || [];
  }

  function aggregateCell(document, rowNode, columnNode, indexes) {
    const record = blankRecord();
    const matrix = document.leaf_matrix || {};
    leavesForNode(rowNode, indexes).forEach(rowLeaf => {
      const columns = matrix[rowLeaf] || {};
      leavesForNode(columnNode, indexes).forEach(columnLeaf => {
        addRecord(record, columns[columnLeaf]);
      });
    });
    return emitRecord(
      record,
      Number(document.min_sample_hint) || 1,
      rowNode.parentId === columnNode.parentId
    );
  }

  function aggregateOverall(document, rowNode, indexes) {
    const record = blankRecord();
    const matrix = document.leaf_matrix || {};
    leavesForNode(rowNode, indexes).forEach(rowLeaf => {
      const columns = matrix[rowLeaf] || {};
      Object.entries(columns).forEach(([columnLeaf, cell]) => {
        const leaf = indexes.leafById.get(columnLeaf);
        if (!leaf) throw new Error(`Unknown canonical leaf: ${columnLeaf}`);
        if (leaf.parent_id !== rowNode.parentId) addRecord(record, cell);
      });
    });
    return emitRecord(record, Number(document.min_sample_hint) || 1, false);
  }

  function buildView(document, expandedRows, expandedColumns) {
    const indexes = buildIndexes(document);
    const rows = axisNodes(document, expandedRows, indexes);
    const columns = axisNodes(document, expandedColumns, indexes);
    const matrix = {};
    const overall = {};
    rows.forEach(row => {
      overall[row.id] = aggregateOverall(document, row, indexes);
      matrix[row.id] = {};
      columns.forEach(column => {
        matrix[row.id][column.id] = aggregateCell(
          document,
          row,
          column,
          indexes
        );
      });
    });
    const expandableParentIds = (document.parent_order || []).filter(parentId => {
      const parent = indexes.parentById.get(parentId);
      return parent && parent.expandable;
    });
    return { rows, columns, matrix, overall, expandableParentIds };
  }

  return { buildView };
});
