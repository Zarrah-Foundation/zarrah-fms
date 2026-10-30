/**
 * Bangladesh address cascade: Division -> District -> Upazila.
 *
 * Data source: a trimmed local copy of the techno-stupid/places-in-bangladesh
 * dataset (static/data/bd/*.json) — no runtime GitHub requests. All three
 * files (8 divisions, 64 districts, 494 upazilas — ~600 rows combined, a few
 * dozen KB) are small enough to fetch once, eagerly, on page load.
 *
 * Union (the smallest administrative tier, ~4,540 nationwide) is entered as
 * free text rather than a fully-populated select — see the project README
 * "Known limitations" section for why, and how to complete it later.
 *
 * Because every dropdown here is populated only with its parent's children,
 * each <select> ends up with a handful to a few dozen options — small enough
 * that the browser's own type-ahead ("searchable") behaviour on a native
 * <select> is fast and fully accessible, without shipping a heavier custom
 * combobox widget.
 */
(function () {
  "use strict";

  var BASE_URL = (document.currentScript && document.currentScript.dataset.baseUrl) || "/static/data/bd/";
  var store = { divisions: [], districts: [], upazilas: [] };

  function lang() {
    return document.documentElement.getAttribute("lang") === "bn" ? "bn" : "en";
  }

  function labelOf(row) {
    return lang() === "bn" ? row.bn : row.name;
  }

  function fillSelect(select, rows, placeholderText, selectedValue) {
    if (!select) return;
    var previous = selectedValue !== undefined ? selectedValue : select.value;
    select.innerHTML = "";
    var placeholderOpt = document.createElement("option");
    placeholderOpt.value = "";
    placeholderOpt.textContent = placeholderText;
    select.appendChild(placeholderOpt);
    rows.forEach(function (row) {
      var opt = document.createElement("option");
      opt.value = row.name;
      opt.textContent = labelOf(row);
      if (row.name === previous) {
        opt.selected = true;
      }
      select.appendChild(opt);
    });
    select.disabled = rows.length === 0;
  }

  function fetchJson(path) {
    return fetch(BASE_URL + path).then(function (res) {
      if (!res.ok) throw new Error("Failed to load " + path);
      return res.json();
    });
  }

  function loadCore() {
    return Promise.all([
      fetchJson("divisions.json"),
      fetchJson("districts.json"),
      fetchJson("upazilas.json"),
    ]).then(function (results) {
      store.divisions = results[0];
      store.districts = results[1];
      store.upazilas = results[2];
    });
  }

  function districtsOf(divisionName) {
    var division = store.divisions.filter(function (d) {
      return d.name === divisionName;
    })[0];
    if (!division) return [];
    return store.districts.filter(function (d) {
      return d.division_id === division.id;
    });
  }

  function upazilasOf(districtName) {
    var district = store.districts.filter(function (d) {
      return d.name === districtName;
    })[0];
    if (!district) return [];
    return store.upazilas.filter(function (u) {
      return u.district_id === district.id;
    });
  }

  /** Wires one Division/District/Upazila group of <select> elements. */
  function wireGroup(ids) {
    var divisionSel = document.getElementById(ids.division);
    var districtSel = document.getElementById(ids.district);
    var upazilaSel = document.getElementById(ids.upazila);
    if (!divisionSel || !districtSel || !upazilaSel) {
      return;
    }

    var t = {
      district: lang() === "bn" ? "জেলা নির্বাচন করুন" : "Select District",
      upazila: lang() === "bn" ? "উপজেলা নির্বাচন করুন" : "Select Upazila",
    };

    function refreshDistricts(keepValue) {
      fillSelect(districtSel, districtsOf(divisionSel.value), t.district, keepValue);
      refreshUpazilas();
    }
    function refreshUpazilas(keepValue) {
      fillSelect(upazilaSel, upazilasOf(districtSel.value), t.upazila, keepValue);
    }

    divisionSel.addEventListener("change", function () {
      refreshDistricts();
    });
    districtSel.addEventListener("change", function () {
      refreshUpazilas();
    });

    // Initial population for whatever division/district is already selected
    // (e.g. after a validation error round-trip where values were retained).
    refreshDistricts(districtSel.value);
    if (districtSel.value) {
      refreshUpazilas(upazilaSel.value);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!document.getElementById("id_present_division")) {
      return; // page doesn't use the address cascade
    }
    loadCore().then(function () {
      wireGroup({ division: "id_present_division", district: "id_present_district", upazila: "id_present_upazila" });
      wireGroup({ division: "id_permanent_division", district: "id_permanent_district", upazila: "id_permanent_upazila" });
    });
  });

  window.ZarrahBdAddress = { districtsOf: districtsOf, upazilasOf: upazilasOf };
})();
