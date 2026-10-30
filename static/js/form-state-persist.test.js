/**
 * Node regression checks for language-switch scroll restore.
 * Run: node static/js/form-state-persist.test.js
 */
"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");
var vm = require("vm");

var src = fs.readFileSync(path.join(__dirname, "form-state-persist.js"), "utf8");

function createSessionStorage() {
  var store = Object.create(null);
  return {
    getItem: function (k) {
      return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null;
    },
    setItem: function (k, v) {
      store[k] = String(v);
    },
    removeItem: function (k) {
      delete store[k];
    },
    _dump: function () {
      return store;
    },
  };
}

function loadModule(options) {
  options = options || {};
  var scrollX = options.scrollX || 0;
  var scrollY = typeof options.scrollY === "number" ? options.scrollY : 0;
  var lang = options.lang || "en";
  var pathname = options.pathname || "/about/";
  var sessionStorage = options.sessionStorage || createSessionStorage();
  var submitHandlers = [];
  var rafQueue = [];

  var form = {
    contains: function () {
      return true;
    },
    addEventListener: function (type, fn) {
      if (type === "submit") submitHandlers.push(fn);
    },
  };

  var languageBtn = {
    name: "language",
    value: options.submitLanguage || "bn",
    type: "submit",
  };

  var context = {
    window: null,
    globalThis: null,
    document: {
      readyState: "complete",
      documentElement: {
        lang: lang,
        scrollTop: scrollY,
        scrollLeft: scrollX,
      },
      body: { scrollTop: scrollY, scrollLeft: scrollX },
      activeElement: languageBtn,
      querySelectorAll: function (sel) {
        if (sel === "[data-language-switch]") return [form];
        if (sel === "form input, form textarea, form select") return [];
        return [];
      },
      addEventListener: function () {},
      getElementsByName: function () {
        return [];
      },
    },
    sessionStorage: sessionStorage,
    location: { pathname: pathname },
    scrollX: scrollX,
    scrollY: scrollY,
    pageXOffset: scrollX,
    pageYOffset: scrollY,
    scrollTo: function (a, b) {
      if (a && typeof a === "object") {
        scrollX = typeof a.left === "number" ? a.left : scrollX;
        scrollY = typeof a.top === "number" ? a.top : scrollY;
      } else {
        scrollX = a || 0;
        scrollY = b || 0;
      }
      context.scrollX = scrollX;
      context.scrollY = scrollY;
      context.pageXOffset = scrollX;
      context.pageYOffset = scrollY;
      context.document.documentElement.scrollTop = scrollY;
      context.document.documentElement.scrollLeft = scrollX;
    },
    requestAnimationFrame: function (cb) {
      rafQueue.push(cb);
      return rafQueue.length;
    },
    setTimeout: function (cb) {
      cb();
      return 1;
    },
    Event: function () {},
    CSS: { escape: function (s) { return s; } },
  };

  context.window = context;
  context.globalThis = context;

  Object.defineProperty(context, "scrollY", {
    get: function () {
      return scrollY;
    },
    set: function (v) {
      scrollY = v;
    },
    configurable: true,
  });
  Object.defineProperty(context, "scrollX", {
    get: function () {
      return scrollX;
    },
    set: function (v) {
      scrollX = v;
    },
    configurable: true,
  });

  vm.runInNewContext(src, context, { filename: "form-state-persist.js" });

  function flushRaf() {
    // Double-rAF restore: run queued callbacks until idle (capped).
    var guard = 0;
    while (rafQueue.length && guard < 20) {
      guard += 1;
      var batch = rafQueue.slice();
      rafQueue.length = 0;
      batch.forEach(function (cb) {
        cb();
      });
    }
  }

  function submitLanguage(value) {
    languageBtn.value = value;
    context.document.activeElement = languageBtn;
    var event = {
      submitter: languageBtn,
      preventDefault: function () {
        event.defaultPrevented = true;
      },
      defaultPrevented: false,
    };
    submitHandlers.forEach(function (fn) {
      fn(event);
    });
    return event;
  }

  return {
    context: context,
    sessionStorage: sessionStorage,
    submitLanguage: submitLanguage,
    flushRaf: flushRaf,
    getScrollY: function () {
      return scrollY;
    },
    setScrollY: function (y) {
      scrollY = y;
      context.scrollY = y;
      context.pageYOffset = y;
    },
    storageKey: function () {
      return context.ZarrahFormState.storageKey();
    },
  };
}

// --- 1) Capture scroll on language-switch submit, restore after "reload" ---
(function () {
  var sessionStorage = createSessionStorage();
  var page1 = loadModule({
    lang: "en",
    scrollY: 1200,
    scrollX: 0,
    pathname: "/about/",
    sessionStorage: sessionStorage,
    submitLanguage: "bn",
  });

  page1.setScrollY(1200);
  var ev = page1.submitLanguage("bn");
  assert.strictEqual(ev.defaultPrevented, false, "switching locale must submit");

  var key = page1.storageKey();
  var raw = sessionStorage.getItem(key);
  assert.ok(raw, "snapshot must be saved before reload");
  var snap = JSON.parse(raw);
  assert.strictEqual(snap.scrollY, 1200);
  assert.strictEqual(snap.scrollX, 0);

  // Simulated redirected page load (new document, same sessionStorage path).
  var page2 = loadModule({
    lang: "bn",
    scrollY: 0,
    scrollX: 0,
    pathname: "/about/",
    sessionStorage: sessionStorage,
  });
  assert.strictEqual(page2.getScrollY(), 0, "fresh load starts at top");

  page2.flushRaf();
  assert.ok(
    Math.abs(page2.getScrollY() - 1200) <= 1,
    "scrollY must be restored after language redirect, got " + page2.getScrollY()
  );
  assert.strictEqual(
    sessionStorage.getItem(key),
    null,
    "snapshot must be cleared after restore"
  );
})();

// --- 2) No saved state → do nothing ---
(function () {
  var page = loadModule({ lang: "en", scrollY: 40, pathname: "/contact/" });
  page.flushRaf();
  assert.strictEqual(page.getScrollY(), 40);
  assert.strictEqual(page.sessionStorage.getItem(page.storageKey()), null);
})();

// --- 3) Already-active language: no capture / no submit ---
(function () {
  var page = loadModule({
    lang: "bn",
    scrollY: 800,
    pathname: "/about/",
    submitLanguage: "bn",
  });
  var ev = page.submitLanguage("bn");
  assert.strictEqual(ev.defaultPrevented, true);
  assert.strictEqual(page.sessionStorage.getItem(page.storageKey()), null);
})();

// --- 4) Must not use a blanket scrollTo(0,0) helper ---
assert.ok(!/scrollTo\(\s*0\s*,\s*0\s*\)/.test(src));

console.log("form-state-persist.test.js: OK");
