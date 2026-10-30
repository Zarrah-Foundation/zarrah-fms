/**
 * Reusable, dependency-free file upload enhancement.
 *
 * Progressively enhances any `<input type="file">` found inside an element
 * marked `data-upload-field` with:
 *  - a drag & drop zone (click or drop to select)
 *  - filename + human-readable size display
 *  - an image preview (when data-image="true") or a file-type icon
 *  - Replace / Remove buttons
 *  - a short simulated progress bar giving feedback that the file was read
 *    and passed client-side validation
 *
 * Browser security note: once a page performs a full server round-trip
 * (i.e. the browser reloads/re-renders the document), no script or server
 * response can re-populate an `<input type="file">` with a previously
 * chosen file — this is enforced by every browser to stop sites silently
 * pre-filling local file paths. This module cannot and does not try to work
 * around that. Instead, `members/apply.html` submits via `fetch()`
 * (see membership-form.js) so validation errors are applied to the *same*
 * DOM/input elements without a page reload, which keeps the selected file
 * (and its preview) intact. The native `<input type="file">` underneath
 * this widget always keeps working even if JavaScript fails to load.
 */
(function () {
  "use strict";

  function humanFileSize(bytes) {
    if (!bytes) return "0 B";
    if (bytes < 1024) return bytes + " B";
    var units = ["KB", "MB", "GB"];
    var i = -1;
    do {
      bytes /= 1024;
      i++;
    } while (bytes >= 1024 && i < units.length - 1);
    return bytes.toFixed(1) + " " + units[i];
  }

  function strings(lang) {
    return lang === "bn"
      ? {
          drag: "ফাইল টেনে ছাড়ুন, বা ",
          browse: "ব্রাউজ করুন",
          replace: "পরিবর্তন করুন",
          remove: "মুছুন",
          removeLabel: "ফাইল মুছুন",
        }
      : {
          drag: "Drag & drop file here, or ",
          browse: "browse",
          replace: "Replace",
          remove: "Remove",
          removeLabel: "Remove file",
        };
  }

  function enhance(wrapper, opts) {
    opts = opts || {};
    var input = wrapper.querySelector('input[type="file"]');
    if (!input || wrapper.dataset.uploadEnhanced) {
      return;
    }
    wrapper.dataset.uploadEnhanced = "true";

    var lang = document.documentElement.getAttribute("lang") === "bn" ? "bn" : "en";
    var t = strings(lang);
    var isImage = wrapper.dataset.image === "true";

    input.classList.add("upload-input-native");
    // The visible drop-zone (below) is the keyboard/pointer control now;
    // keep the native input out of the tab order and non-clickable so it
    // doesn't act as an invisible duplicate control layered on top.
    input.setAttribute("tabindex", "-1");
    input.setAttribute("aria-hidden", "true");

    var zone = document.createElement("div");
    zone.className = "upload-zone";
    zone.setAttribute("tabindex", "0");
    zone.setAttribute("role", "button");
    zone.setAttribute("aria-label", t.browse);

    var idle = document.createElement("div");
    idle.className = "upload-zone-idle";
    idle.innerHTML =
      '<i class="bi bi-cloud-arrow-up upload-zone-icon" aria-hidden="true"></i>' +
      '<p class="upload-zone-text">' + t.drag + '<span class="upload-zone-browse">' + t.browse + "</span></p>" +
      (wrapper.dataset.formats
        ? '<p class="upload-zone-formats">' + wrapper.dataset.formats + "</p>"
        : "");

    var fileRow = document.createElement("div");
    fileRow.className = "upload-file-row";
    fileRow.hidden = true;
    fileRow.innerHTML =
      '<div class="upload-file-preview">' +
      '<img class="upload-preview-img" hidden alt="">' +
      '<i class="bi bi-file-earmark-check-fill upload-file-icon" aria-hidden="true"></i>' +
      "</div>" +
      '<div class="upload-file-meta">' +
      '<p class="upload-file-name"></p>' +
      '<p class="upload-file-size"></p>' +
      '<div class="upload-progress" hidden><div class="upload-progress-bar"></div></div>' +
      "</div>" +
      '<div class="upload-file-actions">' +
      '<button type="button" class="upload-btn upload-btn-replace">' + t.replace + "</button>" +
      '<button type="button" class="upload-btn upload-btn-remove" aria-label="' + t.removeLabel + '">' +
      '<i class="bi bi-trash3" aria-hidden="true"></i></button>' +
      "</div>";

    zone.appendChild(idle);
    zone.appendChild(fileRow);
    wrapper.appendChild(zone);

    var previewImg = fileRow.querySelector(".upload-preview-img");
    var fileIcon = fileRow.querySelector(".upload-file-icon");
    var nameEl = fileRow.querySelector(".upload-file-name");
    var sizeEl = fileRow.querySelector(".upload-file-size");
    var progressWrap = fileRow.querySelector(".upload-progress");
    var progressBar = fileRow.querySelector(".upload-progress-bar");
    var replaceBtn = fileRow.querySelector(".upload-btn-replace");
    var removeBtn = fileRow.querySelector(".upload-btn-remove");

    function runProgress() {
      var pct = 0;
      progressWrap.hidden = false;
      progressBar.style.width = "0%";
      window.clearInterval(fileRow._progressTimer);
      fileRow._progressTimer = window.setInterval(function () {
        pct += 25;
        progressBar.style.width = Math.min(pct, 100) + "%";
        if (pct >= 100) {
          window.clearInterval(fileRow._progressTimer);
          window.setTimeout(function () {
            progressWrap.hidden = true;
          }, 350);
        }
      }, 70);
    }

    function showFile(file) {
      idle.hidden = true;
      fileRow.hidden = false;
      zone.classList.remove("upload-zone-error");
      zone.classList.add("upload-zone-success");
      nameEl.textContent = file.name;
      sizeEl.textContent = humanFileSize(file.size);
      runProgress();

      if (isImage && file.type.indexOf("image/") === 0) {
        var reader = new FileReader();
        reader.onload = function (e) {
          previewImg.src = e.target.result;
          previewImg.hidden = false;
          fileIcon.hidden = true;
        };
        reader.readAsDataURL(file);
      } else {
        previewImg.hidden = true;
        previewImg.src = "";
        fileIcon.hidden = false;
      }
    }

    function reset() {
      idle.hidden = false;
      fileRow.hidden = true;
      previewImg.hidden = true;
      previewImg.src = "";
      progressWrap.hidden = true;
      zone.classList.remove("upload-zone-success", "upload-zone-error");
    }

    function markError() {
      zone.classList.remove("upload-zone-success");
      zone.classList.add("upload-zone-error");
    }

    wrapper._uploadReset = reset;
    wrapper._uploadMarkError = markError;

    input.addEventListener("change", function () {
      var file = input.files && input.files[0];
      if (!file) {
        reset();
        return;
      }
      if (opts.onSelect && opts.onSelect(file) === false) {
        input.value = "";
        reset();
        markError();
        return;
      }
      showFile(file);
    });

    zone.addEventListener("click", function (e) {
      if (e.target.closest(".upload-btn-remove") || e.target.closest(".upload-btn-replace")) {
        return;
      }
      input.click();
    });
    zone.addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });
    replaceBtn.addEventListener("click", function () {
      input.click();
    });
    removeBtn.addEventListener("click", function (e) {
      e.stopPropagation();
      input.value = "";
      reset();
      input.dispatchEvent(new Event("change"));
    });

    ["dragenter", "dragover"].forEach(function (evt) {
      zone.addEventListener(evt, function (e) {
        e.preventDefault();
        zone.classList.add("upload-zone-drag");
      });
    });
    ["dragleave", "drop"].forEach(function (evt) {
      zone.addEventListener(evt, function (e) {
        e.preventDefault();
        zone.classList.remove("upload-zone-drag");
      });
    });
    zone.addEventListener("drop", function (e) {
      var files = e.dataTransfer && e.dataTransfer.files;
      if (files && files.length) {
        input.files = files;
        input.dispatchEvent(new Event("change"));
      }
    });

    // Pre-existing value on an edit form (server round-trip after an error
    // unrelated to this field): show the filename we already have server-side.
    if (wrapper.dataset.existingName) {
      idle.hidden = true;
      fileRow.hidden = false;
      nameEl.textContent = wrapper.dataset.existingName;
      sizeEl.textContent = lang === "bn" ? "পূর্বে নির্বাচিত ফাইল" : "Previously selected file";
      fileIcon.hidden = false;
    }
  }

  function enhanceAll(opts) {
    document.querySelectorAll("[data-upload-field]").forEach(function (wrapper) {
      var inputEl = wrapper.querySelector("input");
      var fieldOpts = opts && inputEl ? opts[inputEl.name] : undefined;
      enhance(wrapper, fieldOpts);
    });
  }

  window.ZarrahFileUpload = { enhance: enhance, enhanceAll: enhanceAll };
})();
