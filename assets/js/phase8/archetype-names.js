(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.P8ArchetypeNames = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  const FORMAT_PATTERN = /^[a-z0-9_-]+$/;
  const ID_PATTERN = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
  const SHA256_PATTERN = /^[0-9a-f]{64}$/;
  const PROVENANCE_FIELDS = [
    "classifier_identity_digest",
    "name_catalog_digest",
    "projection_subject_digest",
  ];

  function hasSupportedContractVersion(document) {
    if (document?.schema_version === "1.0.0") return true;
    if (document?.schema_version !== "1.1.0") return false;
    const provenance = document.provenance;
    return (
      provenance
      && typeof provenance === "object"
      && !Array.isArray(provenance)
      && PROVENANCE_FIELDS.every(field => SHA256_PATTERN.test(provenance[field] || ""))
    );
  }

  function identityId(parentId, subtypeId = null) {
    if (!ID_PATTERN.test(parentId || "") || (subtypeId !== null && !ID_PATTERN.test(subtypeId))) {
      throw new Error("Classifier name contract contains an invalid stable identity");
    }
    return subtypeId === null ? parentId : `${parentId}/${subtypeId}`;
  }

  function normalize(document, expectedFormat) {
    if (
      !document
      || !hasSupportedContractVersion(document)
      || !FORMAT_PATTERN.test(document.format || "")
      || document.format !== expectedFormat
      || !Array.isArray(document.names)
      || !document.names.length
    ) {
      throw new Error(`Invalid classifier name contract for ${expectedFormat}`);
    }
    const names = new Map();
    document.names.forEach(item => {
      const resolvedId = identityId(item?.parent_id, item?.subtype_id ?? null);
      const english = item?.display?.en;
      const chinese = item?.display?.zh;
      if (
        item?.identity_id !== resolvedId
        || typeof english !== "string"
        || !english.trim()
        || typeof chinese !== "string"
        || !chinese.trim()
        || names.has(resolvedId)
      ) {
        throw new Error(`Invalid classifier name entry: ${resolvedId}`);
      }
      names.set(resolvedId, Object.freeze({ en: english, zh: chinese }));
    });
    document.names.forEach(item => {
      if (item.subtype_id !== null && !names.has(item.parent_id)) {
        throw new Error(`Classifier subtype has no parent name: ${item.identity_id}`);
      }
    });
    return Object.freeze({ format: document.format, names });
  }

  function resolve(contract, parentId, subtypeId, language, unknownLabel) {
    if (parentId === "unknown") return unknownLabel;
    if (!contract || (language !== "en" && language !== "zh")) {
      throw new Error("Classifier name lookup is not initialized");
    }
    const key = identityId(parentId, subtypeId ?? null);
    const display = contract.names.get(key);
    if (!display) throw new Error(`Missing approved classifier name: ${contract.format}|${key}`);
    return display[language];
  }

  function resolveIdentity(contract, value, language, unknownLabel) {
    const parts = String(value || "").split("/");
    if (parts.length > 2) throw new Error(`Invalid classifier identity: ${value}`);
    return resolve(contract, parts[0], parts[1] || null, language, unknownLabel);
  }

  function localizeHierarchy(contract, hierarchy, language, unknownLabel) {
    if (!hierarchy || !Array.isArray(hierarchy.parents) || !Array.isArray(hierarchy.leaves)) {
      throw new Error("Classifier hierarchy is missing stable identity collections");
    }
    return {
      ...hierarchy,
      parents: hierarchy.parents.map(parent => ({
        ...parent,
        name: resolve(contract, parent.id, null, language, unknownLabel),
      })),
      leaves: hierarchy.leaves.map(leaf => {
        const name = resolve(
          contract,
          leaf.parent_id,
          leaf.subtype_id ?? null,
          language,
          unknownLabel
        );
        return { ...leaf, name, display_name: name };
      }),
    };
  }

  return Object.freeze({ identityId, localizeHierarchy, normalize, resolve, resolveIdentity });
});
