/**
 * Shared body scroll lock for mobile drawers.
 * Saves/restores scroll for in-page open/close; does not force scroll to top.
 */
(function (global) {
  "use strict";

  var lockedScrollY = 0;
  var isLocked = false;

  function currentScrollY() {
    return global.scrollY || global.pageYOffset || document.documentElement.scrollTop || 0;
  }

  function focusNoScroll(el) {
    if (!el || typeof el.focus !== "function") return;
    try {
      el.focus({ preventScroll: true });
    } catch (err) {
      el.focus();
    }
  }

  /**
   * True when activating this anchor will load a different document
   * (path/search/origin), so scroll restore on the current page is pointless.
   * Same-page hash links and empty/# hrefs are in-page.
   */
  function isLeavingDocument(anchor) {
    if (!anchor || !anchor.getAttribute) return false;
    var raw = anchor.getAttribute("href");
    if (raw == null || raw === "" || raw.charAt(0) === "#") return false;
    if (/^javascript:/i.test(raw)) return false;
    try {
      var url = new URL(anchor.href, global.location.href);
      var cur = global.location;
      if (url.origin !== cur.origin) return true;
      if (url.pathname !== cur.pathname || url.search !== cur.search) return true;
      return false;
    } catch (err) {
      return true;
    }
  }

  function lockBodyScroll() {
    if (isLocked) return lockedScrollY;
    lockedScrollY = currentScrollY();
    isLocked = true;
    var body = document.body;
    body.classList.add("drawer-lock-scroll");
    body.style.position = "fixed";
    body.style.top = "-" + lockedScrollY + "px";
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    return lockedScrollY;
  }

  /**
   * @param {{ restore?: boolean }} [options]
   *   restore (default true): put the viewport back to the pre-lock Y.
   *   Pass restore:false when navigating away so we do not flash-scroll.
   */
  function applyScrollY(y) {
    // Prefer writing scrollTop directly; avoids smooth-scroll interference.
    if (document.documentElement) {
      document.documentElement.scrollTop = y;
    }
    if (document.body) {
      document.body.scrollTop = y;
    }
    if (typeof global.scrollTo === "function") {
      try {
        global.scrollTo({ top: y, left: 0, behavior: "instant" });
      } catch (err) {
        global.scrollTo(0, y);
      }
    }
  }

  function unlockBodyScroll(options) {
    options = options || {};
    var restore = options.restore !== false;
    var y = lockedScrollY;
    if (!isLocked) {
      if (restore) {
        applyScrollY(y);
      }
      return y;
    }
    var body = document.body;
    var html = document.documentElement;
    var prevAnchor = html ? html.style.overflowAnchor : "";
    if (html) {
      // Stop scroll anchoring from shifting Y when fixed positioning is removed.
      html.style.overflowAnchor = "none";
    }
    body.classList.remove("drawer-lock-scroll");
    body.style.position = "";
    body.style.top = "";
    body.style.left = "";
    body.style.right = "";
    body.style.width = "";
    isLocked = false;
    lockedScrollY = 0;
    if (restore) {
      applyScrollY(y);
      global.requestAnimationFrame(function () {
        applyScrollY(y);
        if (html) {
          html.style.overflowAnchor = prevAnchor;
        }
      });
    } else if (html) {
      html.style.overflowAnchor = prevAnchor;
    }
    return y;
  }

  function getLockedScrollY() {
    return lockedScrollY;
  }

  function getIsLocked() {
    return isLocked;
  }

  global.ZFDrawerScroll = {
    lockBodyScroll: lockBodyScroll,
    unlockBodyScroll: unlockBodyScroll,
    focusNoScroll: focusNoScroll,
    isLeavingDocument: isLeavingDocument,
    getLockedScrollY: getLockedScrollY,
    getIsLocked: getIsLocked,
    // test seam: reset internal state without touching DOM styles
    _resetForTests: function () {
      lockedScrollY = 0;
      isLocked = false;
    },
  };
})(typeof window !== "undefined" ? window : globalThis);
