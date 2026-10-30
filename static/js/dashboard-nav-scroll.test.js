/**
 * Node regression: saved sidebar scrollTop preserve + active fallback.
 * Run: node static/js/dashboard-nav-scroll.test.js
 */
"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");
var vm = require("vm");

var src = fs.readFileSync(path.join(__dirname, "dashboard-shell.js"), "utf8");

assert.ok(src.indexOf("captureDashNavScroll") !== -1);
assert.ok(src.indexOf("positionActiveDashboardNav") !== -1);
assert.ok(src.indexOf("zarrah:dash-nav-scroll") !== -1);
assert.ok(src.indexOf("savedY != null") !== -1);
assert.ok(src.indexOf('addEventListener("pagehide"') === -1);
assert.ok(src.indexOf("addEventListener('pagehide'") === -1);
assert.ok(!/scrollIntoView\s*\(/.test(src));
assert.ok(!/window\.scrollTo\s*\(/.test(src));

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
  };
}

function makeContainer(opts) {
  opts = opts || {};
  var scrollTop = opts.scrollTop || 0;
  var clientHeight = opts.clientHeight || 400;
  var scrollHeight = opts.scrollHeight || 2000;
  var containerTop = opts.containerTop || 0;
  var activeOffsetTop = opts.activeOffsetTop;
  var activeHeight = opts.activeHeight || 40;
  var hasActive = opts.hasActive !== false;

  var active = hasActive
    ? {
        getBoundingClientRect: function () {
          var top = containerTop + (activeOffsetTop - scrollTop);
          return {
            top: top,
            bottom: top + activeHeight,
            height: activeHeight,
          };
        },
      }
    : null;

  var container = {
    clientHeight: clientHeight,
    scrollHeight: scrollHeight,
    closest: function (sel) {
      if (sel === "[data-dash-nav-scroll]") return this;
      return null;
    },
    querySelector: function (sel) {
      if (!hasActive) return null;
      if (
        sel === "a.dash-nav-link-active" ||
        sel === 'a[aria-current="page"]'
      ) {
        return active;
      }
      return null;
    },
    getBoundingClientRect: function () {
      return {
        top: containerTop,
        bottom: containerTop + clientHeight,
        height: clientHeight,
      };
    },
  };

  Object.defineProperty(container, "scrollTop", {
    get: function () {
      return scrollTop;
    },
    set: function (v) {
      scrollTop = v;
    },
    configurable: true,
  });

  return container;
}

function loadApi(sessionStorage, containers) {
  sessionStorage = sessionStorage || createSessionStorage();
  containers = containers || [];
  var raf = [];
  var linkHandlers = [];

  var newsLink = {
    getAttribute: function (n) {
      return n === "href" ? "/dashboard/news/" : null;
    },
    closest: function (sel) {
      if (sel === "[data-dash-nav-scroll]") return containers[0] || null;
      return null;
    },
    addEventListener: function (type, fn) {
      if (type === "click") linkHandlers.push(fn);
    },
  };

  var drawer = {
    classList: {
      contains: function () {
        return false;
      },
      add: function () {},
      remove: function () {},
    },
    querySelector: function (sel) {
      if (sel === "[data-dash-nav-scroll]") return containers[1] || containers[0] || null;
      return null;
    },
    querySelectorAll: function () {
      return [];
    },
    setAttribute: function () {},
  };

  var context = {
    window: null,
    document: {
      getElementById: function (id) {
        if (id === "dash-drawer") return drawer;
        if (id === "dash-drawer-backdrop") {
          return {
            removeAttribute: function () {},
            setAttribute: function () {},
            classList: { add: function () {}, remove: function () {} },
          };
        }
        if (id === "dash-drawer-open") {
          return { addEventListener: function () {}, setAttribute: function () {} };
        }
        if (id === "dash-drawer-close") {
          return { addEventListener: function () {} };
        }
        if (id === "notif-mark-all") return null;
        return null;
      },
      querySelectorAll: function (sel) {
        if (sel === "[data-dash-nav-scroll]") return containers;
        if (sel === "[data-dash-nav-scroll] a[href]") return [newsLink];
        if (sel === "[data-dropdown-toggle]") return [];
        if (sel === "[data-dropdown-menu]") return [];
        if (sel === "form.js-notif-mark-read") return [];
        if (sel === "form.js-notif-mark-all") return [];
        if (sel === ".dash-badge-count") return [];
        return [];
      },
      querySelector: function (sel) {
        if (sel === ".dash-sidebar [data-dash-nav-scroll]") return containers[0] || null;
        return null;
      },
      addEventListener: function () {},
      cookie: "",
    },
    sessionStorage: sessionStorage,
    requestAnimationFrame: function (cb) {
      raf.push(cb);
      return raf.length;
    },
    addEventListener: function () {},
    setTimeout: function (cb) {
      cb();
      return 1;
    },
    ZFDrawerScroll: {
      lockBodyScroll: function () {},
      unlockBodyScroll: function () {},
      focusNoScroll: function () {},
      isLeavingDocument: function () {
        return true;
      },
    },
  };
  context.window = context;
  vm.runInNewContext(src, context, { filename: "dashboard-shell.js" });

  function flushRaf() {
    var guard = 0;
    while (raf.length && guard < 20) {
      guard += 1;
      var batch = raf.slice();
      raf.length = 0;
      batch.forEach(function (cb) {
        cb();
      });
    }
  }

  return {
    api: context.ZarrahDashNavScroll,
    sessionStorage: sessionStorage,
    clickNews: function () {
      linkHandlers.forEach(function (fn) {
        fn();
      });
    },
    flushRaf: flushRaf,
  };
}

// 1) Capture on click → new page restores exact scrollTop (wins over active)
(function () {
  var sessionStorage = createSessionStorage();
  var page1Container = makeContainer({
    scrollTop: 600,
    activeOffsetTop: 1200,
  });
  page1Container.scrollTop = 600;
  var page1 = loadApi(sessionStorage, [page1Container]);
  page1.clickNews();
  assert.strictEqual(sessionStorage.getItem("zarrah:dash-nav-scroll"), "600");

  var page2Desktop = makeContainer({
    scrollTop: 0,
    activeOffsetTop: 1200,
  });
  var page2Drawer = makeContainer({
    scrollTop: 0,
    activeOffsetTop: 1200,
  });
  var page2 = loadApi(sessionStorage, [page2Desktop, page2Drawer]);
  page2.flushRaf();
  assert.strictEqual(page2Desktop.scrollTop, 600);
  assert.strictEqual(page2Drawer.scrollTop, 600);
  assert.strictEqual(sessionStorage.getItem("zarrah:dash-nav-scroll"), null);
})();

// 2) No saved position → active positioning runs
(function () {
  var c = makeContainer({
    scrollTop: 0,
    clientHeight: 400,
    scrollHeight: 2000,
    activeOffsetTop: 1200,
  });
  var page = loadApi(createSessionStorage(), [c]);
  page.flushRaf();
  assert.ok(c.scrollTop > 0, "active fallback should move scroll");
})();

// 3) Active already comfortable (no saved) → unchanged
(function () {
  var api = loadApi(createSessionStorage(), []).api;
  var c = makeContainer({
    scrollTop: 100,
    clientHeight: 400,
    scrollHeight: 2000,
    activeOffsetTop: 200,
  });
  var before = c.scrollTop;
  api.positionActive(c);
  assert.strictEqual(c.scrollTop, before);
})();

// 4) Active below / above helpers still work
(function () {
  var api = loadApi(createSessionStorage(), []).api;
  var below = makeContainer({
    scrollTop: 0,
    activeOffsetTop: 1200,
  });
  api.positionActive(below);
  assert.ok(below.scrollTop > 0);

  var above = makeContainer({
    scrollTop: 900,
    activeOffsetTop: 100,
  });
  api.positionActive(above);
  assert.ok(above.scrollTop < 900);
})();

console.log("dashboard-nav-scroll.test.js: OK");
