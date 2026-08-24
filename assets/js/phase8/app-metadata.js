(function (root) {
  "use strict";

  const LANGUAGE_STORAGE_KEY = "mtgmeta-language";
  const SITE_METADATA = {
    zh: {
      title: "猫猫万智周报｜MTGO 环境与精选套牌",
      description: "每周整理 MTGO 标准与摩登的环境变化、套牌数据与精选套牌。",
      locale: "zh_CN",
      footer: {
        source: "卡图与卡牌数据：",
        policyLead: "猫猫万智周报为依据",
        policyLabel: "《爱好者内容政策》",
        policyTail: "制作的非官方爱好者内容，未获 Wizards 批准或认可。部分材料归 Wizards of the Coast LLC 所有。© Wizards of the Coast LLC。",
      },
    },
    en: {
      title: "MTG Meta Analytics | MTGO Metagame & Featured Decks",
      description: "Weekly MTGO Standard and Modern metagame trends, deck data, and featured decks.",
      locale: "en_US",
      footer: {
        source: "Card images and card data:",
        policyLead: "MTG Meta Analytics is unofficial Fan Content permitted under the",
        policyLabel: "Fan Content Policy",
        policyTail: ". Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. © Wizards of the Coast LLC.",
      },
    },
  };

  function isLanguage(value) {
    return value === "zh" || value === "en";
  }

  function storedLanguage(storage) {
    try {
      const value = storage?.getItem(LANGUAGE_STORAGE_KEY);
      return isLanguage(value) ? value : null;
    } catch {
      return null;
    }
  }

  function resolveLanguage(urlLanguage, storage) {
    return isLanguage(urlLanguage) ? urlLanguage : (storedLanguage(storage) || "zh");
  }

  function rememberLanguage(language, storage) {
    if (!isLanguage(language)) return;
    try {
      storage?.setItem(LANGUAGE_STORAGE_KEY, language);
    } catch {
      // Private or unavailable storage must not prevent the selected language from working.
    }
  }

  function normalizedRoute(parameters) {
    const next = new URLSearchParams(parameters);
    if (next.get("product") === "weekly-pickup") {
      next.set("product", "mtgo-landing");
      next.set("section", "features");
    }
    return next;
  }

  function canonicalParameters(parameters) {
    const canonical = new URLSearchParams();
    const format = parameters.get("format");
    const product = parameters.get("product");
    const language = parameters.get("lang");
    if (format) canonical.set("format", format);
    if (product) canonical.set("product", product);
    if (product === "mtgo-landing" && parameters.get("section") === "features") {
      canonical.set("section", "features");
      const week = parameters.get("week");
      if (/^\d{4}-W\d{2}$/.test(week || "")) canonical.set("week", week);
      const feature = parameters.get("feature");
      if (/^deck:[0-9a-f]{20}$/.test(feature || "")) canonical.set("feature", feature);
    }
    if (language) canonical.set("lang", language);
    return canonical;
  }

  function metadataFor(language) {
    return SITE_METADATA[isLanguage(language) ? language : "zh"];
  }

  root.P8Metadata = Object.freeze({
    LANGUAGE_STORAGE_KEY,
    canonicalParameters,
    metadataFor,
    normalizedRoute,
    rememberLanguage,
    resolveLanguage,
  });
})(globalThis);
