"use strict";

(function (root) {
  const MAX_CONCURRENT_IMAGES = 4;
  const MAX_IMAGE_ATTEMPTS = 2;
  const records = new Map();
  const queue = [];
  let active = 0;

  function recordFor(url) {
    if (!records.has(url)) {
      records.set(url, { attempts: 0, status: "idle" });
    }
    return records.get(url);
  }

  function pump() {
    if (document.hidden) return;
    while (active < MAX_CONCURRENT_IMAGES && queue.length) {
      const task = queue.shift();
      const record = recordFor(task.url);
      if (task.cancelled) {
        record.status = "idle";
        task.reject(new Error("cancelled"));
        continue;
      }
      active += 1;
      record.status = "loading";
      record.attempts += 1;
      const probe = new Image();
      probe.onload = () => {
        active -= 1;
        record.status = "loaded";
        record.promise = null;
        task.resolve(task.url);
        pump();
      };
      probe.onerror = () => {
        active -= 1;
        record.status = "failed";
        record.promise = null;
        task.reject(new Error("image"));
        pump();
      };
      probe.src = task.url;
    }
  }

  function load(url, { owner = "default", priority = false, retry = false } = {}) {
    const record = recordFor(url);
    if (record.status === "loaded") return Promise.resolve(url);
    if (record.status === "loading" || record.status === "queued") {
      return record.promise;
    }
    if (record.status === "failed" && (!retry || record.attempts >= MAX_IMAGE_ATTEMPTS)) {
      return Promise.reject(new Error("image"));
    }
    let task;
    const promise = new Promise((resolve, reject) => {
      task = { cancelled: false, owner, reject, resolve, url };
    });
    record.promise = promise;
    record.status = "queued";
    if (priority) queue.unshift(task);
    else queue.push(task);
    pump();
    return promise;
  }

  function cancelQueued(owner) {
    queue.forEach(task => {
      if (task.owner === owner) task.cancelled = true;
    });
  }

  function attempts(url) {
    return recordFor(url).attempts;
  }

  let observer = null;
  function progressiveObserver() {
    if (observer || !("IntersectionObserver" in window)) return observer;
    observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const image = entry.target;
        observer.unobserve(image);
        load(image.dataset.progressiveImage, {
          owner: image.dataset.imageOwner || "view",
        }).then(url => {
          image.src = url;
          image.closest(".card-image-frame")?.classList.replace("is-loading", "is-loaded");
        }).catch(() => {
          image.closest(".card-image-frame")?.classList.replace("is-loading", "is-error");
        });
      });
    }, { rootMargin: "400px 0px" });
    return observer;
  }

  function observe(container = document) {
    container.querySelectorAll("img[data-progressive-image]:not([data-image-observed])")
      .forEach(image => {
        image.dataset.imageObserved = "true";
        const progressive = progressiveObserver();
        if (progressive) progressive.observe(image);
        else {
          load(image.dataset.progressiveImage).then(url => {
            image.src = url;
          }).catch(() => {
            image.closest(".card-image-frame")?.classList.add("is-error");
          });
        }
      });
  }

  document.addEventListener("visibilitychange", pump);

  const images = Object.freeze({
    attempts,
    cancelQueued,
    load,
    observe,
    snapshot() {
      return Object.freeze({ active, queued: queue.filter(task => !task.cancelled).length });
    },
  });
  root.P8CardImages = images;

  const floating = document.querySelector("#card-preview");
  const floatingFrame = floating.querySelector(".card-image-frame");
  const floatingImage = floating.querySelector("img");
  const floatingStatus = floating.querySelector(".card-image-placeholder");
  const modal = document.querySelector("#card-preview-modal");
  const dialog = modal.querySelector(".card-preview-dialog");
  const modalFrame = modal.querySelector(".card-image-frame");
  const modalImage = modal.querySelector("img");
  const modalTitle = modal.querySelector("#card-preview-title");
  const modalStatus = modal.querySelector("[data-card-image-status]");
  const modalRetry = modal.querySelector("[data-card-image-retry]");
  const modalClose = modal.querySelector("[data-card-preview-close]");
  const scryfallLink = modal.querySelector("#card-preview-scryfall");
  const backgroundNodes = [
    document.querySelector(".app-header"),
    document.querySelector(".page-shell"),
    document.querySelector("[data-return-to-top]"),
    document.querySelector(".site-footer"),
  ].filter(Boolean);
  const priorInert = new Map();
  let modalTrigger = null;
  let modalUrl = null;
  let modalName = null;
  let modalOwner = null;
  let modalHistory = false;
  let savedScrollY = 0;

  function touchOnly() {
    return matchMedia("(any-hover: none)").matches;
  }

  function setFrame(frame, status) {
    frame.classList.toggle("is-loading", status === "loading");
    frame.classList.toggle("is-loaded", status === "loaded");
    frame.classList.toggle("is-error", status === "error");
  }

  function loadFloating(link) {
    const url = link.dataset.cardImage;
    const retry = images.attempts(url) === 1;
    floating.hidden = false;
    floating.setAttribute("aria-hidden", "false");
    floatingImage.removeAttribute("src");
    floatingStatus.textContent = t("card.image_loading");
    setFrame(floatingFrame, "loading");
    images.load(url, { owner: "desktop-preview", priority: true, retry })
      .then(loadedUrl => {
        if (floating.hidden || floating.dataset.url !== url) return;
        floatingImage.src = loadedUrl;
        setFrame(floatingFrame, "loaded");
      })
      .catch(() => {
        if (floating.hidden || floating.dataset.url !== url) return;
        floatingStatus.textContent = `${link.dataset.cardName}: ${t("card.image_unavailable")}`;
        setFrame(floatingFrame, "error");
      });
    floating.dataset.url = url;
  }

  function hideFloating() {
    floating.hidden = true;
    floating.setAttribute("aria-hidden", "true");
    floating.removeAttribute("data-url");
    floatingImage.removeAttribute("src");
    images.cancelQueued("desktop-preview");
  }

  function loadModalImage(retry = false) {
    modalImage.removeAttribute("src");
    modalStatus.textContent = retry
      ? t("card.image_retrying")
      : t("card.image_loading");
    modalRetry.hidden = true;
    modalRetry.disabled = true;
    setFrame(modalFrame, "loading");
    images.load(modalUrl, { owner: modalOwner, priority: true, retry })
      .then(url => {
        if (modal.hidden || url !== modalUrl) return;
        modalImage.src = url;
        setFrame(modalFrame, "loaded");
      })
      .catch(() => {
        if (modal.hidden) return;
        modalStatus.textContent = `${modalName}: ${t("card.image_unavailable")}`;
        modalRetry.textContent = t("card.image_retry");
        modalRetry.hidden = images.attempts(modalUrl) >= MAX_IMAGE_ATTEMPTS;
        modalRetry.disabled = false;
        setFrame(modalFrame, "error");
      });
  }

  function restoreBackground() {
    backgroundNodes.forEach(node => {
      node.inert = priorInert.get(node) || false;
    });
    priorInert.clear();
  }

  function finalizeModalClose() {
    if (modal.hidden) return;
    images.cancelQueued(modalOwner);
    modal.hidden = true;
    modal.setAttribute("aria-hidden", "true");
    modalImage.removeAttribute("src");
    document.body.classList.remove("card-modal-open");
    document.body.style.removeProperty("top");
    restoreBackground();
    window.scrollTo(0, savedScrollY);
    modalTrigger?.focus({ preventScroll: true });
    modalTrigger = null;
    modalUrl = null;
    modalName = null;
    modalOwner = null;
    modalHistory = false;
  }

  function dismissModal() {
    if (modal.hidden) return;
    if (modalHistory) window.history.back();
    else finalizeModalClose();
  }

  function openModal(link) {
    hideFloating();
    modalTrigger = link;
    modalUrl = link.dataset.cardImage;
    modalName = link.dataset.cardName || link.textContent.trim();
    modalOwner = `modal:${Date.now()}`;
    savedScrollY = window.scrollY;
    modalTitle.textContent = t("card.preview_title", { name: modalName });
    modalClose.setAttribute("aria-label", t("card.close_preview"));
    scryfallLink.textContent = t("card.view_scryfall");
    scryfallLink.href = link.dataset.scryfallUrl || link.href;
    backgroundNodes.forEach(node => {
      priorInert.set(node, node.inert);
      node.inert = true;
    });
    document.body.style.top = `-${savedScrollY}px`;
    document.body.classList.add("card-modal-open");
    modal.hidden = false;
    modal.setAttribute("aria-hidden", "false");
    try {
      window.history.pushState(
        { ...(window.history.state || {}), cardPreview: true },
        "",
        window.location.href
      );
      modalHistory = true;
    } catch (error) {
      modalHistory = false;
      console.error(error);
    }
    loadModalImage(false);
    modalClose.focus({ preventScroll: true });
  }

  document.addEventListener("click", event => {
    const link = event.target.closest("a[data-card-image]");
    if (link && touchOnly()) {
      event.preventDefault();
      openModal(link);
      return;
    }
    if (event.target.closest("[data-card-preview-close]")) {
      dismissModal();
      return;
    }
    if (event.target === modal) {
      dismissModal();
      return;
    }
    if (event.target.closest("[data-card-image-retry]")) {
      modalRetry.disabled = true;
      loadModalImage(true);
      return;
    }
    if (event.target.closest("#card-preview-scryfall")) {
      setTimeout(dismissModal, 0);
    }
  });

  document.addEventListener("mouseover", event => {
    const link = event.target.closest("a[data-card-image]");
    if (!link || touchOnly() || link.contains(event.relatedTarget)) return;
    loadFloating(link);
  });

  document.addEventListener("mousemove", event => {
    if (floating.hidden) return;
    floating.style.left = `${Math.min(window.innerWidth - 255, event.clientX + 16)}px`;
    floating.style.top = `${Math.max(8, Math.min(window.innerHeight - 345, event.clientY + 16))}px`;
  });

  document.addEventListener("mouseout", event => {
    const link = event.target.closest("a[data-card-image]");
    if (!link || link.contains(event.relatedTarget)) return;
    hideFloating();
  });

  document.addEventListener("focusin", event => {
    const link = event.target.closest("a[data-card-image]");
    if (link && !touchOnly()) loadFloating(link);
  });

  document.addEventListener("focusout", event => {
    if (event.target.closest("a[data-card-image]") && !touchOnly()) hideFloating();
  });

  document.addEventListener("keydown", event => {
    if (modal.hidden) return;
    if (event.key === "Escape") {
      event.preventDefault();
      dismissModal();
      return;
    }
    if (event.key !== "Tab") return;
    const focusable = [...dialog.querySelectorAll("button:not([hidden]), a[href]")]
      .filter(node => !node.disabled);
    const first = focusable[0];
    const last = focusable.at(-1);
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  });

  window.addEventListener("popstate", event => {
    if (modal.hidden) return;
    event.stopImmediatePropagation();
    finalizeModalClose();
  }, { capture: true });

  images.observe(document);
  root.P8CardPreview = Object.freeze({ close: dismissModal, isOpen: () => !modal.hidden });
})(globalThis);
