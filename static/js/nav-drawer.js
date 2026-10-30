/**
 * Accessible slide-in mobile navigation drawer.
 * Progressive enhancement only — the drawer markup degrades to normal
 * (invisible/hidden) content if JS fails to load.
 *
 * Scroll: uses ZFDrawerScroll to preserve viewport Y for in-page open/close.
 * Cross-page link clicks unlock without forcing scroll-to-top.
 */
(function () {
  "use strict";

  document.addEventListener("DOMContentLoaded", function () {
    var openBtn = document.getElementById("drawer-open-btn");
    var closeBtn = document.getElementById("drawer-close-btn");
    var drawer = document.getElementById("mobile-drawer");
    var backdrop = document.getElementById("drawer-backdrop");
    var scrollApi = window.ZFDrawerScroll;

    if (!openBtn || !drawer || !backdrop || !scrollApi) {
      return;
    }

    var lastFocused = null;

    function getFocusable() {
      return Array.prototype.slice.call(
        drawer.querySelectorAll("a[href], button:not([disabled]), select, input")
      );
    }

    function openDrawer() {
      lastFocused = document.activeElement;
      backdrop.hidden = false;
      drawer.classList.add("drawer-panel-open");
      backdrop.classList.add("drawer-backdrop-open");
      drawer.setAttribute("aria-hidden", "false");
      openBtn.setAttribute("aria-expanded", "true");
      scrollApi.lockBodyScroll();

      window.requestAnimationFrame(function () {
        scrollApi.focusNoScroll(drawer);
      });

      document.addEventListener("keydown", onKeydown);
    }

    /**
     * @param {{ restoreScroll?: boolean, restoreFocus?: boolean }} [options]
     */
    function closeDrawer(options) {
      options = options || {};
      var restoreScroll = options.restoreScroll !== false;
      var restoreFocus = options.restoreFocus !== false;

      drawer.classList.remove("drawer-panel-open");
      backdrop.classList.remove("drawer-backdrop-open");
      drawer.setAttribute("aria-hidden", "true");
      openBtn.setAttribute("aria-expanded", "false");
      scrollApi.unlockBodyScroll({ restore: restoreScroll });
      document.removeEventListener("keydown", onKeydown);

      window.setTimeout(function () {
        backdrop.hidden = true;
      }, 300);

      if (restoreFocus) {
        if (lastFocused && typeof lastFocused.focus === "function") {
          scrollApi.focusNoScroll(lastFocused);
        } else {
          scrollApi.focusNoScroll(openBtn);
        }
      }
    }

    function onKeydown(event) {
      if (event.key === "Escape" || event.key === "Esc") {
        closeDrawer();
        return;
      }
      if (event.key === "Tab") {
        var focusable = getFocusable();
        if (focusable.length === 0) {
          return;
        }
        var first = focusable[0];
        var last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          scrollApi.focusNoScroll(last);
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          scrollApi.focusNoScroll(first);
        }
      }
    }

    openBtn.addEventListener("click", openDrawer);
    if (closeBtn) closeBtn.addEventListener("click", function () {
      closeDrawer();
    });
    backdrop.addEventListener("click", function () {
      closeDrawer();
    });

    drawer.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (scrollApi.isLeavingDocument(link)) {
          // Real navigation: unlock without scroll/focus restore (no top jump flash).
          closeDrawer({ restoreScroll: false, restoreFocus: false });
        } else {
          closeDrawer();
        }
      });
    });

    window.addEventListener("resize", function () {
      if (window.innerWidth >= 1024 && drawer.classList.contains("drawer-panel-open")) {
        closeDrawer();
      }
    });
  });
})();
