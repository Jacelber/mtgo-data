(function (root) {
  "use strict";

  const LOOKUP_PATH = "assets/card-localization/cards.json";
  const LOCAL_IMAGE = /^assets\/card-localization\/images\/[0-9a-f]{64}\.webp$/;

  function scryfallImage(englishName) {
    return `https://api.scryfall.com/cards/named?exact=${encodeURIComponent(englishName)}&format=image&version=normal`;
  }

  function scryfallLink(englishName) {
    return `https://scryfall.com/search?q=${encodeURIComponent(`!"${englishName}"`)}`;
  }

  function trustedMtgchImage(value) {
    if (typeof value !== "string") return false;
    try {
      const url = new URL(value);
      return url.protocol === "https:"
        && url.hostname === "images.mtgch.com"
        && url.pathname.startsWith("/zhs/");
    } catch {
      return false;
    }
  }

  function trustedMtgchCard(value) {
    if (typeof value !== "string") return false;
    try {
      const url = new URL(value);
      return url.protocol === "https:"
        && url.hostname === "mtgch.com"
        && !url.port
        && !url.username
        && !url.password
        && !url.search
        && !url.hash
        && /^\/card\/[^/]+\/[^/]+\/?$/.test(url.pathname);
    } catch {
      return false;
    }
  }

  function parseLookup(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) {
      throw new Error("Card-localization lookup must be an object.");
    }
    const parsed = Object.create(null);
    for (const [englishName, entry] of Object.entries(value)) {
      const keys = entry && typeof entry === "object" && !Array.isArray(entry)
        ? Object.keys(entry).sort()
        : [];
      const validKeys = [
        "zh_name",
        "image_url|zh_name",
        "image_url|local_image|zh_name",
        "mtgch_url|zh_name",
        "image_url|mtgch_url|zh_name",
        "image_url|local_image|mtgch_url|zh_name",
      ];
      if (
        !englishName
        || englishName !== englishName.trim()
        || !validKeys.includes(keys.join("|"))
        || typeof entry.zh_name !== "string"
        || !entry.zh_name.trim()
        || (entry.image_url !== undefined && !trustedMtgchImage(entry.image_url))
        || (entry.local_image !== undefined && !LOCAL_IMAGE.test(entry.local_image))
        || (entry.mtgch_url !== undefined && !trustedMtgchCard(entry.mtgch_url))
      ) {
        throw new Error(`Invalid card-localization entry: ${englishName}`);
      }
      parsed[englishName] = Object.freeze({ ...entry });
    }
    return Object.freeze(parsed);
  }

  function resolve(englishName, language, lookup, englishLocalImage = null) {
    const fallbackImage = englishLocalImage || scryfallImage(englishName);
    const fallbackLink = scryfallLink(englishName);
    if (language !== "zh") {
      return Object.freeze({
        displayName: englishName,
        image: fallbackImage,
        source: englishLocalImage ? "english-local" : "english-scryfall",
        linkUrl: fallbackLink,
        linkProvider: "scryfall",
      });
    }
    const entry = lookup?.[englishName];
    if (!entry) {
      return Object.freeze({
        displayName: englishName,
        image: fallbackImage,
        source: englishLocalImage ? "english-local" : "english-scryfall",
        linkUrl: fallbackLink,
        linkProvider: "scryfall",
      });
    }
    const image = entry.local_image || entry.image_url || fallbackImage;
    const source = entry.local_image
      ? "chinese-local"
      : entry.image_url
        ? "chinese-mtgch"
        : englishLocalImage
          ? "english-local"
          : "english-scryfall";
    return Object.freeze({
      displayName: entry.zh_name,
      image,
      source,
      linkUrl: entry.mtgch_url || fallbackLink,
      linkProvider: entry.mtgch_url ? "mtgch" : "scryfall",
    });
  }

  root.P8CardLocalization = Object.freeze({
    LOOKUP_PATH,
    parseLookup,
    resolve,
    scryfallImage,
    scryfallLink,
  });
})(globalThis);
