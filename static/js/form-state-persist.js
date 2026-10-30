/**
 * Reusable form-state persistence across the full-page reload triggered by
 * the language switcher (see includes/_language_switch.html).
 *
 * Django's `set_language` view does a real POST + redirect back to the same
 * URL (LocaleMiddleware architecture is unchanged). Without help, that
 * reload wipes out anything a visitor typed into any form on the page —
 * Membership Application, Donation, Contact, Volunteer, or any future form —
 * and resets the viewport scroll position.
 *
 * This module:
 *   1. Serializes every text/textarea/select/checkbox/radio field on the
 *      page (file inputs are skipped — they can't be restored for security
 *      reasons) into sessionStorage, keyed by the current path, right
 *      before a language-switch form submits — including scrollX/scrollY.
 *   2. Restores those values — scroll (post-layout), fields, and focus on a
 *      best-effort basis — once the page reloads in the new language.
 *   3. Clears the stored snapshot after a restore attempt completes, so a
 *      normal reload/navigation never resurrects stale data.
 *
 * Any form on any page is covered automatically; nothing to wire up beyond
 * loading this script once (done globally in base.html) and marking the
 * language-switch <form> with `data-language-switch` (already set on
 * includes/_language_switch.html).
 *
 * Does not intercept ordinary navigation links.
 */
(function () {
  "use strict";

  var STORAGE_PREFIX = "zarrah:form-state:";
  var RESTORE_RETRY_MS = 300;
  // Cascading selects (BD address, education selector) populate their
  // options asynchronously after a fetch, so a saved <select> value may not
  // have a matching <option> yet on the first attempt. Retry briefly before
  // giving up on any field that hasn't "taken".
  var RESTORE_MAX_ATTEMPTS = 6;

  function storageKey() {
    return STORAGE_PREFIX + window.location.pathname;
  }

  function currentScroll() {
    var x = window.scrollX;
    var y = window.scrollY;
    if (typeof x !== "number") {
      x = window.pageXOffset || (document.documentElement && document.documentElement.scrollLeft) || 0;
    }
    if (typeof y !== "number") {
      y = window.pageYOffset || (document.documentElement && document.documentElement.scrollTop) || 0;
    }
    return { scrollX: x, scrollY: y };
  }

  function isRestorableField(field) {
    if (!field.name || field.name === "csrfmiddlewaretoken") {
      return false;
    }
    var type = (field.type || "").toLowerCase();
    var skip = ["file", "password", "submit", "button", "reset", "hidden", "image"];
    return skip.indexOf(type) === -1;
  }

  function serializeForms() {
    var fields = [];
    var elements = document.querySelectorAll("form input, form textarea, form select");

    Array.prototype.forEach.call(elements, function (field) {
      if (!isRestorableField(field)) {
        return;
      }
      var type = (field.type || "").toLowerCase();
      var entry = { name: field.name, type: type, value: field.value };
      if (type === "checkbox" || type === "radio") {
        entry.checked = field.checked;
      }
      fields.push(entry);
    });

    return fields;
  }

  function serializeActiveField() {
    var el = document.activeElement;
    if (!el || el === document.body || !el.name) {
      return null;
    }
    return { name: el.name, type: (el.type || "").toLowerCase(), value: el.value };
  }

  function capture() {
    try {
      var scroll = currentScroll();
      var snapshot = {
        fields: serializeForms(),
        activeField: serializeActiveField(),
        scrollX: scroll.scrollX,
        scrollY: scroll.scrollY,
        savedAt: Date.now(),
      };
      window.sessionStorage.setItem(storageKey(), JSON.stringify(snapshot));
    } catch (error) {
      // sessionStorage unavailable (private browsing, quota, etc.) — the
      // language switch still works, it just won't restore form/scroll state.
    }
  }

  function elementsNamed(name) {
    if (!name || !window.CSS || !window.CSS.escape) {
      return elementsNamedFallback(name);
    }
    return document.querySelectorAll('[name="' + window.CSS.escape(name) + '"]');
  }

  function elementsNamedFallback(name) {
    var all = document.getElementsByName ? document.getElementsByName(name) : [];
    return all;
  }

  function fireChange(el) {
    // Restored values should behave like real user input so any dependent
    // logic already wired on the page reacts correctly — cascading address
    // selects, education selector, "same as present address" visibility
    // toggles, live-validation icons, etc.
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function setSelectValue(select, value) {
    if (value === "" || value === null || typeof value === "undefined") {
      return true;
    }
    for (var i = 0; i < select.options.length; i++) {
      if (select.options[i].value === value) {
        if (select.value !== value) {
          select.value = value;
          fireChange(select);
        }
        return true;
      }
    }
    return false;
  }

  function applyField(entry) {
    var elements = elementsNamed(entry.name);
    if (!elements.length) {
      return false;
    }

    var applied = false;
    Array.prototype.forEach.call(elements, function (el) {
      if (entry.type === "checkbox") {
        if (elements.length === 1 || el.value === entry.value) {
          if (el.checked !== !!entry.checked) {
            el.checked = !!entry.checked;
            fireChange(el);
          }
          applied = true;
        }
      } else if (entry.type === "radio") {
        if (el.value === entry.value) {
          if (!el.checked) {
            el.checked = true;
            fireChange(el);
          }
          applied = true;
        }
      } else if (el.tagName === "SELECT") {
        applied = setSelectValue(el, entry.value) || applied;
      } else {
        if (el.value !== entry.value) {
          el.value = entry.value;
          fireChange(el);
        }
        applied = true;
      }
    });
    return applied;
  }

  function restoreFocus(activeField) {
    if (!activeField) {
      return;
    }
    var elements = elementsNamed(activeField.name);
    if (!elements.length) {
      return;
    }
    var target = elements[0];
    if (activeField.type === "radio") {
      Array.prototype.forEach.call(elements, function (el) {
        if (el.value === activeField.value) {
          target = el;
        }
      });
    }
    if (target && typeof target.focus === "function") {
      target.focus();
    }
  }

  function readSnapshot() {
    var raw;
    try {
      raw = window.sessionStorage.getItem(storageKey());
    } catch (error) {
      return null;
    }
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw);
    } catch (error) {
      clearSnapshot();
      return null;
    }
  }

  function clearSnapshot() {
    try {
      window.sessionStorage.removeItem(storageKey());
    } catch (error) {
      // ignore
    }
  }

  function hasScroll(snapshot) {
    return !!(snapshot && typeof snapshot.scrollY === "number");
  }

  function hasFields(snapshot) {
    return !!(snapshot && snapshot.fields && snapshot.fields.length);
  }

  function applyScrollPosition(scrollX, scrollY) {
    var x = typeof scrollX === "number" ? scrollX : 0;
    var y = scrollY;
    if (typeof window.scrollTo === "function") {
      try {
        window.scrollTo({ left: x, top: y, behavior: "instant" });
      } catch (err) {
        window.scrollTo(x, y);
      }
      return;
    }
    if (document.documentElement) {
      document.documentElement.scrollLeft = x;
      document.documentElement.scrollTop = y;
    }
    if (document.body) {
      document.body.scrollLeft = x;
      document.body.scrollTop = y;
    }
  }

  /**
   * Restore scroll after layout so bilingual content height changes do not
   * immediately fight the restored position. Uses double rAF (not a long timeout).
   */
  function restoreScrollPosition(snapshot, done) {
    if (!hasScroll(snapshot)) {
      if (done) done();
      return;
    }
    var x = typeof snapshot.scrollX === "number" ? snapshot.scrollX : 0;
    var y = snapshot.scrollY;

    function apply() {
      applyScrollPosition(x, y);
      if (done) done();
    }

    if (typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(apply);
      });
    } else {
      apply();
    }
  }

  function restore() {
    var snapshot = readSnapshot();
    if (!snapshot) {
      return;
    }
    if (!hasFields(snapshot) && !hasScroll(snapshot)) {
      clearSnapshot();
      return;
    }

    function finish() {
      restoreFocus(snapshot.activeField);
      restoreScrollPosition(snapshot, function () {
        clearSnapshot();
      });
    }

    if (!hasFields(snapshot)) {
      finish();
      return;
    }

    var pending = snapshot.fields.slice();
    var attempts = 0;

    function attempt() {
      attempts += 1;
      pending = pending.filter(function (entry) {
        return !applyField(entry);
      });

      if (pending.length && attempts < RESTORE_MAX_ATTEMPTS) {
        window.setTimeout(attempt, RESTORE_RETRY_MS);
      } else {
        finish();
      }
    }

    attempt();
  }

  function isCurrentLanguage(code) {
    if (!code) {
      return false;
    }
    var htmlLang =
      (document.documentElement && document.documentElement.lang) || "";
    return htmlLang.toLowerCase() === String(code).toLowerCase();
  }

  function languageFromSubmitEvent(event, form) {
    var submitter = event.submitter;
    if (submitter && submitter.name === "language") {
      return submitter.value;
    }
    var active = document.activeElement;
    if (active && form.contains(active) && active.name === "language") {
      return active.value;
    }
    return null;
  }

  function attachLanguageSwitchCapture() {
    var forms = document.querySelectorAll("[data-language-switch]");
    Array.prototype.forEach.call(forms, function (form) {
      form.addEventListener("submit", function (event) {
        var lang = languageFromSubmitEvent(event, form);
        // Same locale: skip redundant POST/reload (keyboard + pointer).
        if (lang && isCurrentLanguage(lang)) {
          event.preventDefault();
          return;
        }
        capture();
      });
    });
  }

  window.ZarrahFormState = {
    capture: capture,
    restore: restore,
    storageKey: storageKey,
  };

  function init() {
    restore();
    attachLanguageSwitchCapture();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
