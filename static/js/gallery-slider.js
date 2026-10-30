/**
 * Lightweight accessible homepage gallery slider.
 */
(function () {
  function prefersReducedMotion() {
    return window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function initSlider(root) {
    var track = root.querySelector("[data-zf-track]");
    if (!track) return;
    var slides = Array.prototype.slice.call(track.querySelectorAll("[data-zf-slide]"));
    // Filter empty (inactive filtered in template, but guard)
    slides = slides.filter(function (s) {
      return s.querySelector("img");
    });
    if (!slides.length) {
      root.hidden = true;
      return;
    }

    var index = 0;
    var autoplay = root.getAttribute("data-autoplay") === "1" && !prefersReducedMotion();
    var interval = parseInt(root.getAttribute("data-interval") || "5000", 10);
    if (isNaN(interval) || interval < 2000) interval = 5000;
    var showArrows = root.getAttribute("data-show-arrows") === "1";
    var showDots = root.getAttribute("data-show-dots") === "1";
    var controls = root.querySelector("[data-zf-controls]");
    var dotsRoot = root.querySelector("[data-zf-dots]");
    var timer = null;
    var multi = slides.length > 1;

    function goTo(i) {
      index = (i + slides.length) % slides.length;
      slides.forEach(function (slide, n) {
        var active = n === index;
        slide.classList.toggle("is-active", active);
        slide.setAttribute("aria-hidden", active ? "false" : "true");
      });
      track.style.transform = "translate3d(" + -index * 100 + "%, 0, 0)";
      if (dotsRoot) {
        Array.prototype.forEach.call(dotsRoot.children, function (btn, n) {
          btn.setAttribute("aria-selected", n === index ? "true" : "false");
          btn.classList.toggle("is-active", n === index);
        });
      }
    }

    function next() {
      goTo(index + 1);
    }
    function prev() {
      goTo(index - 1);
    }

    function stopAuto() {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }
    function startAuto() {
      stopAuto();
      if (!autoplay || !multi) return;
      timer = setInterval(next, interval);
    }

    if (multi && showArrows && controls) {
      controls.hidden = false;
      var prevBtn = root.querySelector("[data-zf-prev]");
      var nextBtn = root.querySelector("[data-zf-next]");
      if (prevBtn) prevBtn.addEventListener("click", function () { prev(); startAuto(); });
      if (nextBtn) nextBtn.addEventListener("click", function () { next(); startAuto(); });
    }

    if (multi && showDots && dotsRoot) {
      dotsRoot.hidden = false;
      slides.forEach(function (_, n) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "zf-slider__dot";
        btn.setAttribute("role", "tab");
        btn.setAttribute("aria-label", "Slide " + (n + 1));
        btn.addEventListener("click", function () {
          goTo(n);
          startAuto();
        });
        dotsRoot.appendChild(btn);
      });
    }

    root.setAttribute("tabindex", "0");
    root.addEventListener("keydown", function (e) {
      if (!multi) return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        next();
        startAuto();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        prev();
        startAuto();
      }
    });

    // Touch swipe
    var startX = null;
    track.addEventListener(
      "touchstart",
      function (e) {
        if (!e.changedTouches || !e.changedTouches[0]) return;
        startX = e.changedTouches[0].clientX;
        stopAuto();
      },
      { passive: true }
    );
    track.addEventListener(
      "touchend",
      function (e) {
        if (startX == null || !e.changedTouches || !e.changedTouches[0]) return;
        var dx = e.changedTouches[0].clientX - startX;
        startX = null;
        if (Math.abs(dx) < 40) {
          startAuto();
          return;
        }
        if (dx < 0) next();
        else prev();
        startAuto();
      },
      { passive: true }
    );

    root.addEventListener("mouseenter", stopAuto);
    root.addEventListener("mouseleave", startAuto);
    root.addEventListener("focusin", stopAuto);
    root.addEventListener("focusout", startAuto);

    goTo(0);
    startAuto();
  }

  document.addEventListener("DOMContentLoaded", function () {
    Array.prototype.forEach.call(document.querySelectorAll("[data-zf-slider]"), initSlider);
  });
})();
