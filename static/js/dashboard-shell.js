(function () {
  "use strict";

  function getCookie(name) {
    var m = document.cookie.match("(^|;)\\s*" + name + "\\s*=\\s*([^;]+)");
    return m ? m.pop() : "";
  }

  function closeAllMenus(except) {
    document.querySelectorAll("[data-dropdown-menu]").forEach(function (menu) {
      if (menu !== except) {
        menu.setAttribute("hidden", "");
        var t = document.querySelector('[data-dropdown-toggle="' + menu.id + '"]');
        if (t) t.setAttribute("aria-expanded", "false");
      }
    });
  }

  // ---- Dashboard nav scroll ----
  // Priority after normal <a href> navigation:
  //   1) Restore scrollTop captured on the click that started navigation
  //   2) Else positionActiveDashboardNav() for direct loads
  //   3) Else leave default
  // Does NOT use window.scrollTo / scrollIntoView. Does NOT collapse groups.
  // Does NOT use pagehide as primary capture (drawer may already be closed).
  var DASH_NAV_SCROLL_KEY = "zarrah:dash-nav-scroll";
  var ACTIVE_NAV_PAD = 48;
  // Remember a restored navigation scroll for drawer-open / lg resize re-apply.
  var lastRestoredNavScrollY = null;

  function getNavScrollContainers() {
    return Array.prototype.slice.call(
      document.querySelectorAll("[data-dash-nav-scroll]")
    );
  }

  function clearDashNavScroll() {
    try {
      window.sessionStorage.removeItem(DASH_NAV_SCROLL_KEY);
    } catch (err) {
      // ignore
    }
  }

  function readSavedNavScrollY() {
    var raw;
    try {
      raw = window.sessionStorage.getItem(DASH_NAV_SCROLL_KEY);
    } catch (err) {
      return null;
    }
    if (raw == null || raw === "") {
      return null;
    }
    var y = parseFloat(raw);
    if (!isFinite(y) || y < 0) {
      return null;
    }
    return y;
  }

  function clampScrollTop(container, y) {
    var max = Math.max(0, (container.scrollHeight || 0) - (container.clientHeight || 0));
    if (y < 0) {
      return 0;
    }
    if (y > max) {
      return max;
    }
    return y;
  }

  function findActiveNavLink(container) {
    if (!container || !container.querySelector) {
      return null;
    }
    return (
      container.querySelector("a.dash-nav-link-active") ||
      container.querySelector('a[aria-current="page"]')
    );
  }

  /**
   * Adjust container.scrollTop so the active nav link is within padded bounds.
   * Returns true when an active item was found (positioning attempted or skipped
   * because already comfortable).
   */
  function positionActiveDashboardNav(container) {
    if (!container) {
      return false;
    }
    var active = findActiveNavLink(container);
    if (!active) {
      return false;
    }

    var containerRect = container.getBoundingClientRect();
    var activeRect = active.getBoundingClientRect();
    var height = containerRect.height || container.clientHeight || 0;
    if (height <= 0) {
      return true;
    }

    var pad = ACTIVE_NAV_PAD;
    if (height < pad * 2 + 8) {
      pad = Math.max(8, Math.floor(height / 4));
    }

    var delta = 0;
    if (activeRect.top < containerRect.top + pad) {
      delta = activeRect.top - containerRect.top - pad;
    } else if (activeRect.bottom > containerRect.bottom - pad) {
      delta = activeRect.bottom - containerRect.bottom + pad;
    }

    if (delta !== 0) {
      container.scrollTop = clampScrollTop(container, container.scrollTop + delta);
    }
    return true;
  }

  function applySavedNavScrollY(container, y) {
    if (!container || typeof y !== "number") {
      return;
    }
    container.scrollTop = clampScrollTop(container, y);
  }

  function captureDashNavScroll(fromEl) {
    var container =
      fromEl && fromEl.closest
        ? fromEl.closest("[data-dash-nav-scroll]")
        : null;
    if (!container || typeof container.scrollTop !== "number") {
      return;
    }
    lastRestoredNavScrollY = container.scrollTop;
    try {
      window.sessionStorage.setItem(
        DASH_NAV_SCROLL_KEY,
        String(container.scrollTop)
      );
    } catch (err) {
      // sessionStorage unavailable — navigation still proceeds normally
    }
  }

  function runDashboardNavPositioning() {
    var savedY = readSavedNavScrollY();
    getNavScrollContainers().forEach(function (container) {
      if (savedY != null) {
        applySavedNavScrollY(container, savedY);
      } else {
        positionActiveDashboardNav(container);
      }
    });
    if (savedY != null) {
      lastRestoredNavScrollY = savedY;
    }
    clearDashNavScroll();
  }

  function scheduleDashboardNavPositioning() {
    function apply() {
      runDashboardNavPositioning();
    }
    if (typeof window.requestAnimationFrame === "function") {
      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(apply);
      });
    } else {
      apply();
    }
  }

  function reapplyNavScrollOrActive(container) {
    if (!container) {
      return;
    }
    if (typeof lastRestoredNavScrollY === "number") {
      applySavedNavScrollY(container, lastRestoredNavScrollY);
      return;
    }
    positionActiveDashboardNav(container);
  }

  function positionDrawerNavIfPresent() {
    if (!drawer) {
      return;
    }
    var container = drawer.querySelector("[data-dash-nav-scroll]");
    reapplyNavScrollOrActive(container);
  }

  function positionDesktopNavIfPresent() {
    var desktop = document.querySelector(".dash-sidebar [data-dash-nav-scroll]");
    reapplyNavScrollOrActive(desktop);
  }

  function attachDashboardNavPositioning() {
    // Capture before navigation (and before drawer close handlers).
    document.querySelectorAll("[data-dash-nav-scroll] a[href]").forEach(function (link) {
      link.addEventListener("click", function () {
        // Do not preventDefault — normal Django navigation must proceed.
        captureDashNavScroll(link);
      });
    });
    scheduleDashboardNavPositioning();
  }

  window.ZarrahDashNavScroll = {
    STORAGE_KEY: DASH_NAV_SCROLL_KEY,
    capture: captureDashNavScroll,
    positionActive: positionActiveDashboardNav,
    run: runDashboardNavPositioning,
    schedule: scheduleDashboardNavPositioning,
    clear: clearDashNavScroll,
    findActive: findActiveNavLink,
  };

  // ---- Dropdown menus (notifications, user) ----
  document.querySelectorAll("[data-dropdown-toggle]").forEach(function (btn) {
    var menu = document.getElementById(btn.getAttribute("data-dropdown-toggle"));
    if (!menu) return;
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var isOpen = !menu.hasAttribute("hidden");
      closeAllMenus(isOpen ? null : menu);
      if (isOpen) {
        menu.setAttribute("hidden", "");
        btn.setAttribute("aria-expanded", "false");
      } else {
        menu.removeAttribute("hidden");
        btn.setAttribute("aria-expanded", "true");
      }
    });
  });

  document.addEventListener("click", function (e) {
    document.querySelectorAll("[data-dropdown-menu]").forEach(function (menu) {
      if (!menu.hasAttribute("hidden") && !menu.contains(e.target)) {
        menu.setAttribute("hidden", "");
      }
    });
  });

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") closeAllMenus(null);
  });

  // ---- Mobile sidebar drawer (preserve scroll; no focus-driven jump) ----
  var drawer = document.getElementById("dash-drawer");
  var backdrop = document.getElementById("dash-drawer-backdrop");
  var openBtn = document.getElementById("dash-drawer-open");
  var closeBtn = document.getElementById("dash-drawer-close");
  var scrollApi = window.ZFDrawerScroll;

  attachDashboardNavPositioning();

  function openDrawer() {
    if (!drawer || !backdrop || !scrollApi) return;
    backdrop.removeAttribute("hidden");
    scrollApi.lockBodyScroll();
    requestAnimationFrame(function () {
      backdrop.classList.add("drawer-backdrop-open");
      drawer.classList.add("drawer-panel-open");
      // Re-apply saved nav scroll (or active fallback) after drawer is visible.
      positionDrawerNavIfPresent();
      scrollApi.focusNoScroll(drawer);
    });
    drawer.setAttribute("aria-hidden", "false");
    if (openBtn) openBtn.setAttribute("aria-expanded", "true");
  }

  /**
   * @param {{ restoreScroll?: boolean, restoreFocus?: boolean }} [options]
   */
  function closeDrawer(options) {
    if (!drawer || !backdrop || !scrollApi) return;
    options = options || {};
    var restoreScroll = options.restoreScroll !== false;
    var restoreFocus = options.restoreFocus !== false;
    drawer.classList.remove("drawer-panel-open");
    backdrop.classList.remove("drawer-backdrop-open");
    drawer.setAttribute("aria-hidden", "true");
    if (openBtn) openBtn.setAttribute("aria-expanded", "false");
    scrollApi.unlockBodyScroll({ restore: restoreScroll });
    setTimeout(function () {
      backdrop.setAttribute("hidden", "");
    }, 300);
    if (restoreFocus && openBtn) {
      scrollApi.focusNoScroll(openBtn);
    }
  }

  if (openBtn) openBtn.addEventListener("click", openDrawer);
  if (closeBtn) closeBtn.addEventListener("click", function () {
    closeDrawer();
  });
  if (backdrop) backdrop.addEventListener("click", function () {
    closeDrawer();
  });

  if (drawer && scrollApi) {
    drawer.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        if (scrollApi.isLeavingDocument(link)) {
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
      if (window.innerWidth >= 1024) {
        positionDesktopNavIfPresent();
      }
    });

    document.addEventListener("keydown", function (e) {
      if (
        e.key === "Escape" &&
        drawer.classList.contains("drawer-panel-open")
      ) {
        closeDrawer();
      }
    });
  }

  // ---- Notifications: mark all read (bell) ----
  var markAll = document.getElementById("notif-mark-all");
  if (markAll) {
    markAll.addEventListener("click", function () {
      fetch(markAll.getAttribute("data-url"), {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
      }).then(function (r) {
        if (r.ok) window.location.reload();
      });
    });
  }

  function updateBadge(unread) {
    document.querySelectorAll(".dash-badge-count").forEach(function (badge) {
      if (unread > 0) {
        badge.textContent = String(unread);
        badge.hidden = false;
      } else {
        badge.hidden = true;
      }
    });
  }

  // ---- Notifications: AJAX mark-read on list page ----
  document.querySelectorAll("form.js-notif-mark-read").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
        body: new FormData(form),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (!data || !data.ok) return;
          var row = form.closest("[data-notif-row]");
          if (row) {
            row.classList.remove("notif-unread");
            form.remove();
            var badge = row.querySelector(".badge-primary");
            if (badge) badge.remove();
          }
          updateBadge(data.unread || 0);
        })
        .catch(function () {
          form.submit();
        });
    });
  });

  document.querySelectorAll("form.js-notif-mark-all").forEach(function (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      fetch(form.action, {
        method: "POST",
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest",
          Accept: "application/json",
        },
        body: new FormData(form),
      })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          if (data && data.ok) window.location.reload();
        })
        .catch(function () {
          form.submit();
        });
    });
  });
})();
