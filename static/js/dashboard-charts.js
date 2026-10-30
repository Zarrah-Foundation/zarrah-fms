/**
 * Renders the admin dashboard charts with Chart.js (loaded via CDN in
 * templates/dashboard/index.html). Reads chart data from data-* attributes
 * so no inline JavaScript or inline JSON assignment is needed in templates.
 */
(function () {
  "use strict";

  function parseJSON(value, fallback) {
    if (!value) return fallback;
    try {
      return JSON.parse(value);
    } catch (e) {
      return fallback;
    }
  }

  function baseOptions(extra) {
    return Object.assign(
      {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: "bottom", labels: { boxWidth: 12, font: { size: 12 } } } },
        scales: {
          y: { beginAtZero: true, grid: { color: "rgba(229,231,235,.6)" } },
          x: { grid: { display: false } },
        },
      },
      extra || {}
    );
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (typeof window.Chart === "undefined") {
      return;
    }

    var financeCanvas = document.getElementById("finance-chart");
    if (financeCanvas) {
      new window.Chart(financeCanvas, {
        type: "bar",
        data: {
          labels: parseJSON(financeCanvas.dataset.labels, []),
          datasets: [
            {
              label: financeCanvas.dataset.incomeLabel || "Income",
              data: parseJSON(financeCanvas.dataset.income, []),
              backgroundColor: "#0b6b3a",
              borderRadius: 6,
            },
            {
              label: financeCanvas.dataset.expenseLabel || "Expense",
              data: parseJSON(financeCanvas.dataset.expense, []),
              backgroundColor: "#dc2626",
              borderRadius: 6,
            },
          ],
        },
        options: baseOptions(),
      });
    }

    var donationCanvas = document.getElementById("donation-trend-chart");
    if (donationCanvas) {
      new window.Chart(donationCanvas, {
        type: "line",
        data: {
          labels: parseJSON(donationCanvas.dataset.labels, []),
          datasets: [
            {
              label: donationCanvas.dataset.label || "Donations",
              data: parseJSON(donationCanvas.dataset.values, []),
              borderColor: "#d4a017",
              backgroundColor: "rgba(212,160,23,.15)",
              fill: true,
              tension: 0.35,
              pointBackgroundColor: "#d4a017",
            },
          ],
        },
        options: baseOptions(),
      });
    }

    var membershipCanvas = document.getElementById("membership-growth-chart");
    if (membershipCanvas) {
      new window.Chart(membershipCanvas, {
        type: "line",
        data: {
          labels: parseJSON(membershipCanvas.dataset.labels, []),
          datasets: [
            {
              label: membershipCanvas.dataset.label || "New Members",
              data: parseJSON(membershipCanvas.dataset.values, []),
              borderColor: "#0f766e",
              backgroundColor: "rgba(15,118,110,.15)",
              fill: true,
              tension: 0.35,
              pointBackgroundColor: "#0f766e",
            },
          ],
        },
        options: baseOptions(),
      });
    }
  });
})();
