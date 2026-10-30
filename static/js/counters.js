/**
 * Animated count-up for [data-counter] elements.
 *
 * Markup contract:
 *   <span data-counter data-counter-target="500" data-counter-suffix="+">0</span>
 *
 * - Counts up from 0 to data-counter-target once the element scrolls into view.
 * - Respects prefers-reduced-motion (jumps straight to the final value).
 * - No dependencies; safe to include on any page via {% block extra_js %}.
 */
(function () {
  "use strict";

  var SELECTOR = "[data-counter]";
  var DURATION = 1400;

  function formatValue(value, suffix) {
    return Math.round(value).toLocaleString("en-US") + (suffix || "");
  }

  function animateCounter(el) {
    var target = parseFloat(el.getAttribute("data-counter-target") || el.textContent) || 0;
    var suffix = el.getAttribute("data-counter-suffix") || "";
    var prefersReducedMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (prefersReducedMotion) {
      el.textContent = formatValue(target, suffix);
      return;
    }

    var startTime = null;

    function step(timestamp) {
      if (startTime === null) {
        startTime = timestamp;
      }
      var progress = Math.min((timestamp - startTime) / DURATION, 1);
      var eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = formatValue(target * eased, suffix);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    }

    window.requestAnimationFrame(step);
  }

  function init() {
    var elements = document.querySelectorAll(SELECTOR);
    if (!elements.length) {
      return;
    }

    if (!("IntersectionObserver" in window)) {
      elements.forEach ? elements.forEach(animateCounter) : Array.prototype.forEach.call(elements, animateCounter);
      return;
    }

    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.4 }
    );

    Array.prototype.forEach.call(elements, function (el) {
      observer.observe(el);
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
