(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.P8ReviewData = api;
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

  function matchesSearch(value, query) {
    return normalizeSearch(value).includes(query);
  }

  function axisNodes(document, expandedParents, indexes, searchQuery = "") {
    const expanded = new Set(expandedParents || []);
    const query = normalizeSearch(searchQuery);
    const nodes = [];
    (document.parent_order || []).forEach(parentId => {
      const parent = indexes.parentById.get(parentId);
      if (!parent) throw new Error(`排序中存在未知类型：${parentId}`);
      const parentMatch = !query || matchesSearch(parent.display_name || parent.name, query);
      const matchingSubtypeIds = (parent.subtype_ids || []).filter(leafId => {
        const leaf = indexes.leafById.get(leafId);
        if (!leaf) throw new Error(`未知子类型：${leafId}`);
        return matchesSearch(leaf.display_name || leaf.name, query);
      });
      if (!parentMatch && matchingSubtypeIds.length === 0) return;
      nodes.push({
        id: parent.id,
        kind: "archetype",
        name: parent.name,
        parentId,
        parentName: parent.name,
        expandable: Boolean(parent.expandable),
        showAxisToggle: Boolean(parent.expandable),
      });
      const visibleSubtypeIds = query && !parentMatch
        ? matchingSubtypeIds
        : parent.expandable && expanded.has(parentId)
          ? parent.subtype_ids
          : [];
      visibleSubtypeIds.forEach(leafId => {
          const leaf = indexes.leafById.get(leafId);
          if (!leaf) throw new Error(`未知子类型：${leafId}`);
          nodes.push({
            id: leaf.id,
            kind: "subtype",
            name: leaf.display_name || leaf.name,
            parentId,
            parentName: parent.name,
            expandable: false,
            showAxisToggle: false,
          });
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

  function buildVisibleView(document, expandedRows, expandedColumns, searchQuery = "") {
    const indexes = buildIndexes(document);
    const rows = axisNodes(document, expandedRows, indexes, searchQuery);
    const columns = axisNodes(document, expandedColumns, indexes);
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
    return { rows, columns, matrix, overall, expandableParentIds };
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
    buildView,
    buildVisibleView,
    literalRecord,
    normalizeSearch,
    publicPath,
  };
});
