/**
 * Progressive Flatpickr date picker for Django date fields.
 *
 * Keeps the submitted value as Y-m-d (Django DateField / DateInput)
 * while displaying dd/mm/yyyy to the visitor. If Flatpickr fails to load,
 * the native <input type="date"> remains fully usable.
 *
 * Enhance any field marked [data-date-picker], or call
 * ZarrahDatePicker.enhance(el) directly.
 */
(function () {
  "use strict";

  function enhance(input) {
    if (!input || input.dataset.datePickerReady === "true") {
      return null;
    }
    if (typeof window.flatpickr !== "function") {
      return null;
    }

    var maxAttr = input.getAttribute("max");
    var minAttr = input.getAttribute("min");
    var existing = input.value;

    // Flatpickr works best with a text input; keep name/id/classes intact
    // so Django POST, labels, and validation JS continue to work.
    if (input.type === "date") {
      input.type = "text";
    }
    input.setAttribute("placeholder", input.getAttribute("placeholder") || "dd/mm/yyyy");
    input.setAttribute("autocomplete", "bday");
    input.setAttribute("inputmode", "numeric");

    var fp = window.flatpickr(input, {
      dateFormat: "Y-m-d",
      altInput: true,
      altFormat: "d/m/Y",
      allowInput: true,
      disableMobile: false,
      maxDate: maxAttr || "today",
      minDate: minAttr || undefined,
      defaultDate: existing || undefined,
      ariaDateFormat: "d/m/Y",
      onReady: function (selectedDates, dateStr, instance) {
        if (instance.altInput) {
          instance.altInput.className = input.className;
          instance.altInput.setAttribute(
            "aria-required",
            input.getAttribute("aria-required") || "false"
          );
          instance.altInput.id = input.id + "_display";
          var label = document.querySelector('label[for="' + input.id + '"]');
          if (label) {
            instance.altInput.setAttribute(
              "aria-label",
              label.textContent.replace(/\s*\*\s*$/, "").trim()
            );
            label.addEventListener("click", function (event) {
              event.preventDefault();
              instance.open();
              instance.altInput.focus();
            });
          }
        }
      },
      onChange: function () {
        input.dispatchEvent(new Event("input", { bubbles: true }));
        input.dispatchEvent(new Event("change", { bubbles: true }));
      },
    });

    input.dataset.datePickerReady = "true";
    return fp;
  }

  function enhanceAll(root) {
    var scope = root || document;
    var nodes = scope.querySelectorAll("[data-date-picker], #id_date_of_birth");
    Array.prototype.forEach.call(nodes, enhance);
  }

  window.ZarrahDatePicker = { enhance: enhance, enhanceAll: enhanceAll };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      enhanceAll();
    });
  } else {
    enhanceAll();
  }
})();
