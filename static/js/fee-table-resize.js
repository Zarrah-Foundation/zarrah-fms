(function () {
  function initResizableTable(table) {
    if (!table || table.dataset.resizeReady === "1") return;
    table.dataset.resizeReady = "1";
    var storageKey = table.getAttribute("data-storage-key") || "zf-table-cols";
    var ths = Array.prototype.slice.call(table.querySelectorAll("thead th"));
    var minW = 72;
    var maxW = 480;
    var saved = {};
    try {
      saved = JSON.parse(localStorage.getItem(storageKey) || "{}") || {};
    } catch (e) {
      saved = {};
    }

    ths.forEach(function (th, index) {
      var col = th.getAttribute("data-col") || String(index);
      if (saved[col]) {
        var w = Math.min(maxW, Math.max(minW, parseInt(saved[col], 10) || 0));
        if (w) th.style.width = w + "px";
      }
      th.style.position = "relative";
      var handle = document.createElement("span");
      handle.className = "col-resize-handle";
      handle.setAttribute("aria-hidden", "true");
      th.appendChild(handle);

      var startX = 0;
      var startW = 0;
      function onMove(ev) {
        var dx = ev.pageX - startX;
        var next = Math.min(maxW, Math.max(minW, startW + dx));
        th.style.width = next + "px";
      }
      function onUp() {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
        document.body.classList.remove("col-resizing");
        try {
          var map = JSON.parse(localStorage.getItem(storageKey) || "{}") || {};
          map[col] = parseInt(th.style.width, 10) || th.offsetWidth;
          localStorage.setItem(storageKey, JSON.stringify(map));
        } catch (err) {}
      }
      handle.addEventListener("mousedown", function (ev) {
        ev.preventDefault();
        startX = ev.pageX;
        startW = th.offsetWidth;
        document.body.classList.add("col-resizing");
        document.addEventListener("mousemove", onMove);
        document.addEventListener("mouseup", onUp);
      });
    });
  }

  function boot() {
    document.querySelectorAll("table.fee-resizable-table").forEach(initResizableTable);
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
