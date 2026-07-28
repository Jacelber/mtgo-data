(function (root) {
  "use strict";

  function publicPath(path) {
    if (typeof path !== "string" || !path.startsWith("stats/")) {
      throw new Error(`目录中存在不受支持的公开路径：${path}`);
    }
    return `../../../${path}`;
  }

  function dirname(path) {
    return path.split("/").slice(0, -1).join("/");
  }

  function joinPath(base, child) {
    if (child.startsWith("stats/")) return child;
    return `${base.replace(/\/$/, "")}/${child.replace(/^\//, "")}`;
  }

  function createJsonClient(scope, admit) {
    const cache = new Map();

    async function fetchJson(path) {
      if (!admit(path)) {
        throw new Error(`${scope} 不允许读取公开路径：${path}`);
      }
      if (!cache.has(path)) {
        cache.set(path, fetch(publicPath(path)).then(async response => {
          if (!response.ok) throw new Error(`${path}：HTTP ${response.status}`);
          return response.json();
        }));
      }
      return cache.get(path);
    }

    return Object.freeze({
      fetchJson,
      clear() {
        cache.clear();
      },
      scope,
    });
  }

  const catalog = createJsonClient(
    "产品目录",
    path => path === "stats/catalog.json"
  );

  root.P8Runtime = Object.freeze({
    catalog,
    createJsonClient,
    dirname,
    joinPath,
    publicPath,
  });
})(globalThis);
