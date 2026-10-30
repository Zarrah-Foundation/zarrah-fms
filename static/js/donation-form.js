/**
 * Donation form progressive enhancement:
 *  - Render CMS quick-amount chips for the selected category
 *  - Clicking a chip fills the amount field
 *  - Category cards can deep-link / focus the form
 */
(function () {
  "use strict";

  function readAmounts() {
    var el = document.getElementById("donation-quick-amounts");
    if (!el) return {};
    try {
      return JSON.parse(el.textContent || "{}");
    } catch (e) {
      return {};
    }
  }

  function init() {
    var form = document.getElementById("donation-form");
    if (!form) return;

    var categorySelect =
      form.querySelector("[data-donation-category]") || form.querySelector("#id_category");
    var amountInput =
      form.querySelector("[data-donation-amount]") || form.querySelector("#id_amount");
    var chips = document.getElementById("quick-amount-chips");
    if (!categorySelect || !amountInput || !chips) return;

    var amountsByCategory = readAmounts();
    var lang = document.documentElement.getAttribute("lang") === "bn" ? "bn" : "en";
    var currencyPrefix = "৳";

    function renderChips() {
      var key = categorySelect.value;
      var rows = (key && amountsByCategory[key]) || [];
      chips.innerHTML = "";
      if (!rows.length) {
        chips.hidden = true;
        return;
      }
      chips.hidden = false;
      rows.forEach(function (row) {
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className =
          "rounded-xl border border-gray-300 bg-white px-3.5 py-2 text-sm font-semibold text-ink shadow-sm transition-all duration-200 hover:border-primary hover:text-primary";
        btn.textContent = row.label || currencyPrefix + Math.round(row.amount);
        if (!row.label) {
          btn.textContent = currencyPrefix + Math.round(row.amount);
        }
        btn.setAttribute(
          "aria-label",
          (lang === "bn" ? "পরিমাণ নির্বাচন করুন " : "Select amount ") + row.amount
        );
        btn.addEventListener("click", function () {
          amountInput.value = row.amount;
          amountInput.dispatchEvent(new Event("input", { bubbles: true }));
          amountInput.focus();
          Array.prototype.forEach.call(chips.querySelectorAll("button"), function (b) {
            b.classList.remove("border-primary", "bg-primary/5", "text-primary");
          });
          btn.classList.add("border-primary", "bg-primary/5", "text-primary");
        });
        chips.appendChild(btn);
      });
    }

    categorySelect.addEventListener("change", renderChips);
    renderChips();

    var anonymousCheckbox =
      form.querySelector("[data-donation-anonymous]") || form.querySelector("#id_is_anonymous");
    var nameInput =
      form.querySelector("[data-donation-name]") || form.querySelector("#id_donor_name");
    var previousName = nameInput ? nameInput.value : "";

    function syncAnonymous() {
      if (!anonymousCheckbox || !nameInput) return;
      if (anonymousCheckbox.checked) {
        if (nameInput.value !== "Anonymous") {
          previousName = nameInput.value;
        }
        nameInput.value = "Anonymous";
        nameInput.readOnly = true;
        nameInput.setAttribute("aria-readonly", "true");
        nameInput.classList.add("opacity-70");
      } else {
        nameInput.readOnly = false;
        nameInput.removeAttribute("aria-readonly");
        nameInput.classList.remove("opacity-70");
        if (nameInput.value === "Anonymous") {
          nameInput.value = previousName || "";
        }
      }
    }

    if (anonymousCheckbox) {
      anonymousCheckbox.addEventListener("change", syncAnonymous);
      syncAnonymous();
    }

    document.querySelectorAll("[data-select-category]").forEach(function (link) {
      link.addEventListener("click", function (event) {
        // Allow navigation for shareable URLs, but also update the form when
        // the user is already on this page without a full reload.
        var id = link.getAttribute("data-select-category");
        if (!id || !categorySelect.querySelector('option[value="' + id + '"]')) {
          return;
        }
        if (window.location.pathname.indexOf("/donation") === 0) {
          event.preventDefault();
          categorySelect.value = id;
          categorySelect.dispatchEvent(new Event("change", { bubbles: true }));
          form.scrollIntoView({ behavior: "smooth", block: "start" });
          amountInput.focus();
        }
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
