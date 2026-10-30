/**
 * Sticky TOC active-section highlight + reading progress for Constitution page.
 * Progressive enhancement only — page works fully without this script.
 */
(function () {
  var links = document.querySelectorAll("[data-toc-link]");
  var bar = document.getElementById("constitution-toc-bar");
  if (!links.length) return;

  var map = {};
  var ids = [];
  links.forEach(function (a) {
    var id = a.getAttribute("data-toc-link");
    map[id] = a;
    ids.push(id);
  });

  function setActive(id) {
    links.forEach(function (a) {
      a.removeAttribute("aria-current");
    });
    if (map[id]) map[id].setAttribute("aria-current", "true");
    if (bar && ids.length) {
      var idx = ids.indexOf(id);
      if (idx >= 0) {
        bar.style.width = (((idx + 1) / ids.length) * 100).toFixed(1) + "%";
      }
    }
  }

  if ("IntersectionObserver" in window) {
    var observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;
          setActive(entry.target.id);
        });
      },
      { rootMargin: "-18% 0px -62% 0px", threshold: 0 }
    );
    ids.forEach(function (id) {
      var el = document.getElementById(id);
      if (el) observer.observe(el);
    });
  }

  // Initial progress state
  if (bar) bar.style.width = (100 / Math.max(ids.length, 1)).toFixed(1) + "%";
  if (ids[0]) setActive(ids[0]);
})();
