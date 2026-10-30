/**
 * Node regression checks for drawer-scroll-lock.js (no browser required).
 * Run: node static/js/drawer-scroll-lock.test.js
 */
"use strict";

var assert = require("assert");
var fs = require("fs");
var path = require("path");
var vm = require("vm");

var src = fs.readFileSync(path.join(__dirname, "drawer-scroll-lock.js"), "utf8");

function makeAnchor(href, base) {
  base = base || "https://example.com/about/";
  var resolved;
  try {
    resolved = new URL(href, base).href;
  } catch (e) {
    resolved = href;
  }
  return {
    href: resolved,
    getAttribute: function (name) {
      if (name === "href") return href;
      return null;
    },
  };
}

function loadApi(locationHref) {
  var scrollY = 480;
  var bodyStyles = {};
  var bodyClass = "";
  var context = {
    window: null,
    globalThis: null,
    document: {
      documentElement: { scrollTop: 0 },
      body: {
        classList: {
          add: function (c) {
            bodyClass += " " + c;
          },
          remove: function (c) {
            bodyClass = bodyClass.split(c).join("");
          },
          contains: function (c) {
            return bodyClass.indexOf(c) !== -1;
          },
        },
        style: bodyStyles,
      },
    },
    location: new URL(locationHref),
    scrollY: scrollY,
    pageYOffset: scrollY,
    scrollTo: function (x, y) {
      if (typeof x === "object" && x) {
        scrollY = x.top || 0;
      } else {
        scrollY = y || 0;
      }
      context.scrollY = scrollY;
      context.pageYOffset = scrollY;
    },
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
  vm.runInNewContext(src, context);
  return {
    api: context.ZFDrawerScroll,
    getScrollY: function () {
      return scrollY;
    },
    setScrollY: function (y) {
      scrollY = y;
      context.scrollY = y;
      context.pageYOffset = y;
    },
    bodyStyles: bodyStyles,
  };
}

var harness = loadApi("https://example.com/about/");
var api = harness.api;

assert.ok(api, "ZFDrawerScroll exported");
assert.strictEqual(api.isLeavingDocument(makeAnchor("#section")), false);
assert.strictEqual(api.isLeavingDocument(makeAnchor("")), false);
assert.strictEqual(api.isLeavingDocument(makeAnchor("/about/")), false);
assert.strictEqual(api.isLeavingDocument(makeAnchor("/about/#team")), false);
assert.strictEqual(api.isLeavingDocument(makeAnchor("/contact/")), true);
assert.strictEqual(api.isLeavingDocument(makeAnchor("https://other.example/")), true);

harness.setScrollY(640);
api.lockBodyScroll();
assert.strictEqual(api.getIsLocked(), true);
assert.strictEqual(api.getLockedScrollY(), 640);
assert.strictEqual(harness.bodyStyles.position, "fixed");
assert.strictEqual(harness.bodyStyles.top, "-640px");

api.unlockBodyScroll({ restore: true });
assert.strictEqual(api.getIsLocked(), false);
assert.strictEqual(harness.getScrollY(), 640, "in-page unlock restores saved Y");
assert.strictEqual(harness.bodyStyles.position, "");

harness.setScrollY(320);
api.lockBodyScroll();
api.unlockBodyScroll({ restore: false });
assert.strictEqual(
  harness.getScrollY(),
  320,
  "leaving-document unlock must not force scrollTo(0,0)"
);

console.log("drawer-scroll-lock.test.js: OK");
