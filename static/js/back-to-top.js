/**
 * Global Back to Top control (public site base layout).
 * Progressive enhancement — page works without this script.
 */
(function () {
  var btn = document.getElementById("back-to-top");
  if (!btn) return;

  var THRESHOLD = 400;
  var reduceMotion =
    window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ticking = false;
  var visible = false;

  function setVisible(next) {
    if (next === visible) return;
    visible = next;
    if (next) {
      btn.classList.add("is-visible");
      btn.setAttribute("aria-hidden", "false");
      btn.removeAttribute("tabindex");
    } else {
      btn.classList.remove("is-visible");
      btn.setAttribute("aria-hidden", "true");
      btn.setAttribute("tabindex", "-1");
    }
  }

  function update() {
    ticking = false;
    var y = window.scrollY || document.documentElement.scrollTop || 0;
    setVisible(y > THRESHOLD);
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(update);
  }

  btn.addEventListener("click", function () {
    if (reduceMotion) {
      window.scrollTo(0, 0);
      return;
    }
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  window.addEventListener("scroll", onScroll, { passive: true });
  update();
})();
