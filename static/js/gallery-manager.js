/**
 * Homepage Gallery Manager — upload preview, media library picker, reorder.
 */
(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }
  function qsa(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  function syncOrder() {
    var cards = qsa("[data-gallery-cards] [data-membership-id]");
    var ids = cards
      .map(function (el) {
        return el.getAttribute("data-membership-id");
      })
      .filter(Boolean);
    var input = qs("#gallery-order");
    if (input) input.value = ids.join(",");
    cards.forEach(function (card, index) {
      var orderInput = qs('input[name$="-order"]', card);
      if (orderInput) orderInput.value = String(index + 1);
    });
  }

  function bindMoveButtons() {
    var root = qs("[data-gallery-cards]");
    if (!root) return;
    root.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-move]");
      if (!btn) return;
      var card = btn.closest("[data-membership-id]");
      if (!card) return;
      if (btn.getAttribute("data-move") === "up" && card.previousElementSibling) {
        card.parentNode.insertBefore(card, card.previousElementSibling);
      }
      if (btn.getAttribute("data-move") === "down" && card.nextElementSibling) {
        card.parentNode.insertBefore(card.nextElementSibling, card);
      }
      syncOrder();
    });
  }

  function bindUploadPreview() {
    var input = qs("#id_new_gallery_images");
    var preview = qs("#new-upload-preview");
    if (!input || !preview) return;
    // Hide raw file input visually if wrapped in label styling
    input.classList.add("sr-only");
    input.addEventListener("change", function () {
      preview.innerHTML = "";
      var files = input.files || [];
      if (!files.length) {
        preview.hidden = true;
        return;
      }
      preview.hidden = false;
      Array.prototype.forEach.call(files, function (file) {
        if (!file.type || file.type.indexOf("image/") !== 0) return;
        var url = URL.createObjectURL(file);
        var fig = document.createElement("figure");
        fig.className = "overflow-hidden rounded-lg border border-border/60";
        fig.innerHTML =
          '<img src="' +
          url +
          '" alt="" class="h-24 w-full object-cover">' +
          '<figcaption class="truncate px-2 py-1 text-[11px] text-ink-light"></figcaption>';
        fig.querySelector("figcaption").textContent = file.name;
        preview.appendChild(fig);
      });
    });
  }

  function selectedMediaIds() {
    return qsa('#media-library-body input[type="checkbox"][data-media-id]:checked:not(:disabled)').map(
      function (el) {
        return el.value;
      }
    );
  }

  function updateSelectedCount() {
    var el = qs("[data-selected-count]");
    if (el) el.textContent = String(selectedMediaIds().length);
  }

  function bindMediaLibrary() {
    var openBtn = qs("#open-media-library");
    var dialog = qs("#media-library-dialog");
    var body = qs("#media-library-body");
    var closeBtn = qs("#close-media-library");
    var cancelBtn = qs("#cancel-media-library");
    var addBtn = qs("#add-selected-media");
    var attachInput = qs("#id_attach_media_ids");
    if (!openBtn || !dialog || !body) return;

    function close() {
      if (typeof dialog.close === "function") dialog.close();
      else dialog.removeAttribute("open");
    }

    function open() {
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.setAttribute("open", "open");
    }

    function loadLibrary(url) {
      body.innerHTML = "<p class='text-sm text-ink-light'>Loading…</p>";
      fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" }, credentials: "same-origin" })
        .then(function (r) {
          return r.json();
        })
        .then(function (data) {
          var results = data.results || [];
          if (!results.length) {
            body.innerHTML =
              "<p class='text-sm text-ink-light'>No images in the library yet. Upload new images first.</p>";
            return;
          }
          var html = '<div class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4" data-media-grid>';
          results.forEach(function (item) {
            html +=
              '<label class="relative block cursor-pointer rounded-lg border border-border/70 p-2' +
              (item.in_gallery ? " opacity-60" : "") +
              '">' +
              '<input type="checkbox" class="absolute left-3 top-3" value="' +
              item.id +
              '" data-media-id="' +
              item.id +
              '"' +
              (item.in_gallery ? " disabled checked" : "") +
              ">" +
              (item.url
                ? '<img src="' +
                  item.url +
                  '" alt="" class="mb-2 h-28 w-full rounded object-cover" loading="lazy" width="240" height="112">'
                : "") +
              '<p class="truncate text-xs font-medium text-ink">' +
              (item.name || "") +
              "</p>" +
              '<p class="text-[11px] text-ink-light">' +
              (item.created || "") +
              (item.in_gallery ? " · Already in gallery" : "") +
              "</p></label>";
          });
          html += "</div><p class='mt-3 text-sm text-ink-light'><span data-selected-count>0</span> selected</p>";
          body.innerHTML = html;
          body.addEventListener("change", updateSelectedCount);
          updateSelectedCount();
        })
        .catch(function () {
          body.innerHTML = "<p class='text-sm text-danger'>Could not load the media library.</p>";
        });
    }

    openBtn.addEventListener("click", function () {
      loadLibrary(openBtn.getAttribute("data-library-url") || "/dashboard/cms/media/?format=json");
      open();
    });
    if (closeBtn) closeBtn.addEventListener("click", close);
    if (cancelBtn) cancelBtn.addEventListener("click", close);
    if (addBtn) {
      addBtn.addEventListener("click", function () {
        var ids = selectedMediaIds();
        if (attachInput) {
          var existing = (attachInput.value || "")
            .split(",")
            .map(function (s) {
              return s.trim();
            })
            .filter(Boolean);
          ids.forEach(function (id) {
            if (existing.indexOf(id) === -1) existing.push(id);
          });
          attachInput.value = existing.join(",");
        }
        close();
        if (ids.length) {
          var note = document.createElement("p");
          note.className = "text-sm text-primary";
          note.textContent = ids.length + " existing image(s) will be added when you save.";
          var manager = qs("#gallery-manager-title");
          if (manager && manager.parentNode) manager.parentNode.appendChild(note);
        }
      });
    }
  }

  function bindSubmitOrder() {
    var form = qs("#cms-section-form");
    if (!form) return;
    form.addEventListener("submit", function () {
      syncOrder();
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    bindMoveButtons();
    bindUploadPreview();
    bindMediaLibrary();
    bindSubmitOrder();
    syncOrder();
  });
})();
