(function (root) {
  "use strict";

  function entryBase() {
    const configured = globalThis.document?.documentElement?.dataset?.statsBase;
    const base = configured || "../../../";
    if (!/^(?:\.\/|\.\.\/)+$/.test(base)) {
      throw new Error(`Unsupported public data base path: ${base}`);
    }
    return base.endsWith("/") ? base : `${base}/`;
  }

  function publicPath(path) {
    if (
      typeof path !== "string"
      || !path.startsWith("stats/")
      || path.split("/").includes("..")
    ) {
      throw new Error(`Unsupported public data path: ${path}`);
    }
    return `${entryBase()}${path}`;
  }

  function dirname(path) {
    return path.split("/").slice(0, -1).join("/");
  }

  function joinPath(base, child) {
    if (child.startsWith("stats/")) return child;
    return `${base.replace(/\/$/, "")}/${child.replace(/^\//, "")}`;
  }

  class ResourceError extends Error {
    constructor(code, path, details = {}) {
      super(`${code}: ${path}`);
      this.name = "ResourceError";
      this.code = code;
      this.path = path;
      Object.assign(this, details);
    }
  }

  function fingerprint(text) {
    let hash = 2166136261;
    for (let index = 0; index < text.length; index += 1) {
      hash ^= text.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return `${text.length}:${(hash >>> 0).toString(16)}`;
  }

  function createJsonClient(scope, admit, options = {}) {
    const successful = new Map();
    const foregroundRequests = new Map();
    const refreshRequests = new Map();
    const maxEntries = options.maxEntries ?? 24;
    const maxBytes = options.maxBytes ?? 16 * 1024 * 1024;
    const foregroundTimeoutMs = options.foregroundTimeoutMs ?? 30_000;
    const refreshTimeoutMs = options.refreshTimeoutMs ?? 15_000;
    let successfulBytes = 0;

    function assertAdmitted(path) {
      if (!admit(path)) {
        throw new Error(`${scope} does not admit public path: ${path}`);
      }
    }

    function touch(path) {
      const entry = successful.get(path);
      if (!entry) return null;
      successful.delete(path);
      successful.set(path, entry);
      return entry;
    }

    function evict() {
      while (
        successful.size > 1
        && (successful.size > maxEntries || successfulBytes > maxBytes)
      ) {
        const oldestPath = successful.keys().next().value;
        const oldest = successful.get(oldestPath);
        successful.delete(oldestPath);
        successfulBytes -= oldest.bytes;
      }
    }

    function commitEntries(entries) {
      entries.forEach(entry => {
        const previous = successful.get(entry.path);
        if (previous) successfulBytes -= previous.bytes;
        successful.delete(entry.path);
        successful.set(entry.path, entry);
        successfulBytes += entry.bytes;
      });
      evict();
    }

    async function requestEntry(path, { refresh = false, timeoutMs } = {}) {
      assertAdmitted(path);
      const controller = new AbortController();
      const limit = timeoutMs ?? (refresh ? refreshTimeoutMs : foregroundTimeoutMs);
      const timer = setTimeout(() => controller.abort(), limit);
      try {
        const response = await fetch(publicPath(path), {
          cache: refresh ? "no-cache" : "default",
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new ResourceError("http", path, { status: response.status });
        }
        const text = await response.text();
        let value;
        try {
          value = JSON.parse(text);
        } catch (error) {
          throw new ResourceError("invalid", path, { cause: error });
        }
        return {
          bytes: new TextEncoder().encode(text).byteLength,
          fingerprint: fingerprint(text),
          loadedAt: Date.now(),
          path,
          value,
        };
      } catch (error) {
        if (error instanceof ResourceError) throw error;
        if (controller.signal.aborted) {
          throw new ResourceError("timeout", path, { cause: error });
        }
        throw new ResourceError("network", path, { cause: error });
      } finally {
        clearTimeout(timer);
      }
    }

    function sharedRequest(path, refresh) {
      const requests = refresh ? refreshRequests : foregroundRequests;
      if (!requests.has(path)) {
        const request = requestEntry(path, { refresh })
          .finally(() => requests.delete(path));
        requests.set(path, request);
      }
      return requests.get(path);
    }

    async function fetchJson(path) {
      assertAdmitted(path);
      const cached = touch(path);
      if (cached) return cached.value;
      const entry = await sharedRequest(path, false);
      commitEntries([entry]);
      return entry.value;
    }

    async function stage(paths) {
      const uniquePaths = [...new Set(paths)];
      uniquePaths.forEach(assertAdmitted);
      const entries = await Promise.all(
        uniquePaths.map(path => sharedRequest(path, true))
      );
      const changed = entries.some(entry => (
        successful.get(entry.path)?.fingerprint !== entry.fingerprint
      ));
      const values = Object.freeze(Object.fromEntries(
        entries.map(entry => [entry.path, entry.value])
      ));
      let committed = false;
      return Object.freeze({
        changed,
        get(path) {
          return values[path];
        },
        paths: Object.freeze([...uniquePaths]),
        values,
        commit() {
          if (committed) return;
          committed = true;
          commitEntries(entries);
        },
      });
    }

    return Object.freeze({
      clear() {
        successful.clear();
        foregroundRequests.clear();
        refreshRequests.clear();
        successfulBytes = 0;
      },
      fetchJson,
      invalidate(path) {
        const entry = successful.get(path);
        if (!entry) return;
        successful.delete(path);
        successfulBytes -= entry.bytes;
      },
      snapshot() {
        return Object.freeze({
          inFlight: foregroundRequests.size + refreshRequests.size,
          successBytes: successfulBytes,
          successPaths: Object.freeze([...successful.keys()]),
        });
      },
      scope,
      stage,
    });
  }

  const catalog = createJsonClient(
    "catalog",
    path => path === "stats/catalog.json",
    { maxBytes: 1024 * 1024, maxEntries: 1 }
  );

  root.P8Runtime = Object.freeze({
    catalog,
    createJsonClient,
    dirname,
    joinPath,
    publicPath,
    ResourceError,
  });
})(globalThis);
