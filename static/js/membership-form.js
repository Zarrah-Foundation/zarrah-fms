/**
 * Membership application form interactivity:
 *  - Division -> District -> Upazila -> Union cascading, searchable selects
 *    (see bd-address.js) fed by the local Bangladesh geo dataset
 *  - Permanent address "same as present" auto-copy
 *  - Expatriate toggle (hides BD address, shows foreign address fields)
 *  - Student toggle (hides workplace fields, locks occupation to "Student")
 *  - Fully conditional, no-free-text education selector
 *    (Type -> Stage/Marhala/Level -> Class -> Current Status)
 *  - Drag & drop file upload widgets (see file-upload.js) with client-side
 *    size/type validation
 *  - Live bilingual validation for name/phone/email/NID/age fields
 *  - AJAX submission that preserves file selections on validation errors
 *  - Section-jump progress nav
 */
(function () {
  "use strict";

  var MAX_FILE_BYTES = 3 * 1024 * 1024;
  var BANGLA_NAME_RE = /^[\u0980-\u09FF.\s]+$/;
  var ENGLISH_NAME_RE = /^[A-Za-z.\s]+$/;
  var BD_PHONE_RE = /^(?:\+?880|0)1[3-9]\d{8}$/;
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  var NID_RE = /^\d{10}$|^\d{13}$|^\d{17}$/;
  var MIN_AGE = 18;


  function messages(lang) {
    var bn = {
      required: "এই ফিল্ড আবশ্যক।",
      bangla: "শুধুমাত্র বাংলা অক্ষর ব্যবহার করুন।",
      english: "শুধুমাত্র ইংরেজি অক্ষর ব্যবহার করুন।",
      phone: "সঠিক বাংলাদেশি ফোন নম্বর দিন (যেমন ০১XXXXXXXXX)।",
      email: "সঠিক ইমেইল ঠিকানা দিন।",
      nid: "সঠিক NID/জন্ম নিবন্ধন নম্বর দিন (১০, ১৩ বা ১৭ ডিজিট)।",
      age: "সদস্য হতে বয়স কমপক্ষে ১৮ বছর হতে হবে।",
      fileSize: "ফাইলের আকার সর্বোচ্চ ৩ এমবি হতে পারবে।",
      fileType: "শুধুমাত্র JPG, PNG অথবা PDF ফাইল গ্রহণযোগ্য।",
      submitError: "ফর্মে কিছু ভুল আছে। দয়া করে চিহ্নিত ফিল্ডগুলো ঠিক করুন।",
      networkError: "সংযোগ সমস্যা হয়েছে, ফর্মটি সাধারণভাবে জমা দেওয়া হচ্ছে...",
    };
    var en = {
      required: "This field is required.",
      bangla: "Only Bangla characters are allowed.",
      english: "Only English characters are allowed.",
      phone: "Enter a valid Bangladeshi phone number (e.g. 01XXXXXXXXX).",
      email: "Enter a valid email address.",
      nid: "Enter a valid NID/Birth Registration number (10, 13 or 17 digits).",
      age: "You must be at least 18 years old to apply for membership.",
      fileSize: "File size must not exceed 3MB.",
      fileType: "Only JPG, PNG or PDF files are allowed.",
      submitError: "There are some errors in the form. Please fix the highlighted fields.",
      networkError: "Connection problem — submitting the form normally...",
    };
    return lang === "bn" ? bn : en;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var form = document.getElementById("membership-application-form");
    if (!form) {
      return;
    }

    var lang = document.documentElement.getAttribute("lang") === "bn" ? "bn" : "en";
    var msg = messages(lang);

    function fieldIcon(field) {
      var wrap = field.closest(".field-wrap");
      return wrap ? wrap.querySelector("[data-field-icon]") : null;
    }

    function setIcon(field, state) {
      var icon = fieldIcon(field);
      if (!icon) return;
      icon.className =
        "bi field-wrap-icon validation-icon" +
        (state === "valid" ? " bi-check-circle-fill is-valid" : state === "invalid" ? " bi-x-circle-fill is-invalid" : "");
    }

    function syncAltInputState(field) {
      // Flatpickr hides the original input and shows an altInput; keep the
      // visible control's border state in sync with validation feedback.
      if (field._flatpickr && field._flatpickr.altInput) {
        var alt = field._flatpickr.altInput;
        alt.classList.toggle("field-valid", field.classList.contains("field-valid"));
        alt.classList.toggle("field-invalid", field.classList.contains("field-invalid"));
        if (field.getAttribute("aria-invalid") === "true") {
          alt.setAttribute("aria-invalid", "true");
        } else {
          alt.removeAttribute("aria-invalid");
        }
      }
    }

    function fieldError(field, text) {
      var wrap = field.closest(".form-group") || field.parentElement;
      var errorEl = wrap.querySelector(".form-error-js");
      if (!errorEl) {
        errorEl = document.createElement("p");
        errorEl.className = "form-error form-error-js";
        errorEl.setAttribute("role", "alert");
        wrap.appendChild(errorEl);
      }
      errorEl.textContent = text;
      field.setAttribute("aria-invalid", "true");
      field.classList.remove("field-valid");
      field.classList.add("field-invalid");
      setIcon(field, "invalid");
      syncAltInputState(field);
    }

    // Neutral state (e.g. an empty, untouched, or optional field) — no
    // error message, no green/red border.
    function clearError(field) {
      var wrap = field.closest(".form-group") || field.parentElement;
      var errorEl = wrap.querySelector(".form-error-js");
      if (errorEl) {
        errorEl.textContent = "";
      }
      field.removeAttribute("aria-invalid");
      field.classList.remove("field-invalid", "field-valid");
      setIcon(field, "neutral");
      syncAltInputState(field);
    }

    // Confirmed-valid, non-empty input — shows a green border/check so the
    // visitor gets positive feedback without needing to submit the form.
    function fieldValid(field) {
      var wrap = field.closest(".form-group") || field.parentElement;
      var errorEl = wrap.querySelector(".form-error-js");
      if (errorEl) {
        errorEl.textContent = "";
      }
      field.removeAttribute("aria-invalid");
      field.classList.remove("field-invalid");
      field.classList.add("field-valid");
      setIcon(field, "valid");
      syncAltInputState(field);
    }

    // Division -> District -> Upazila -> Union cascading selects are wired
    // by bd-address.js (loaded alongside this script), which owns the full
    // local Bangladesh geo dataset.

    // ---- Permanent address: same as present ----
    // The permanent_* fields are simply hidden when checked — the
    // authoritative copy of present -> permanent happens server-side in
    // MemberApplicationForm.save(). We don't try to mirror the cascading
    // Division/District/Upazila/Union selects here on the client because
    // each select's option list depends on independently-loaded async data;
    // the server copy is both simpler and always correct.
    var sameAsPresent = document.getElementById("id_permanent_same_as_present");
    var permanentFieldsBlock = document.getElementById("permanent-address-fields");

    function syncPermanentVisibility() {
      if (!sameAsPresent || !permanentFieldsBlock) {
        return;
      }
      permanentFieldsBlock.hidden = sameAsPresent.checked;
    }

    if (sameAsPresent) {
      sameAsPresent.addEventListener("change", syncPermanentVisibility);
      syncPermanentVisibility();
    }

    // ---- Expatriate toggle ----
    var isExpat = document.getElementById("id_is_expat");
    var bdAddressBlock = document.getElementById("bd-address-fields");
    var expatFieldsBlock = document.getElementById("expat-fields");

    function syncExpatVisibility() {
      if (!isExpat) {
        return;
      }
      var expat = isExpat.checked;
      if (bdAddressBlock) bdAddressBlock.hidden = expat;
      if (expatFieldsBlock) expatFieldsBlock.hidden = !expat;
    }

    if (isExpat) {
      isExpat.addEventListener("change", syncExpatVisibility);
      syncExpatVisibility();
    }

    // ---- Student toggle ----
    var isStudent = document.getElementById("id_is_student");
    var workplaceBlock = document.getElementById("workplace-fields");
    var occupationField = document.getElementById("id_occupation");

    function syncStudentVisibility() {
      if (!isStudent) {
        return;
      }
      var student = isStudent.checked;
      if (workplaceBlock) workplaceBlock.hidden = student;
      if (occupationField) {
        if (student) {
          occupationField.dataset.prevValue = occupationField.value;
          occupationField.value = lang === "bn" ? "শিক্ষার্থী" : "Student";
          occupationField.setAttribute("readonly", "readonly");
        } else {
          occupationField.removeAttribute("readonly");
          occupationField.value = occupationField.dataset.prevValue || "";
        }
      }
    }

    if (isStudent) {
      isStudent.addEventListener("change", syncStudentVisibility);
      syncStudentVisibility();
    }

    // ---- Education: fully conditional selector (no free text) ----
    // General -> Stage -> Class -> Current Status
    // Qaumi/Alia/Technical -> Marhala/Level -> Current Status
    var educationType = document.getElementById("id_education_type");
    var educationLevel = document.getElementById("id_education_level");
    var educationClass = document.getElementById("id_education_class");
    var educationClassField = document.getElementById("education-class-field");
    var educationStatus = document.getElementById("id_education_status");
    var educationDetailBlock = document.getElementById("education-detail-fields");

    var educationData = { types: [], stages: {}, classes: {} };
    var educationDataEl = document.getElementById("education-data");
    if (educationDataEl) {
      try {
        educationData = JSON.parse(educationDataEl.textContent || "{}");
      } catch (e) {
        educationData = { types: [], stages: {}, classes: {} };
      }
    }

    function optionLabel(opt) {
      return lang === "bn" ? opt.bn : opt.en;
    }

    function fillSelect(select, options, placeholder, selectedValue) {
      if (!select) return;
      select.innerHTML = "";
      var placeholderOpt = document.createElement("option");
      placeholderOpt.value = "";
      placeholderOpt.textContent = placeholder;
      select.appendChild(placeholderOpt);
      options.forEach(function (opt) {
        var el = document.createElement("option");
        el.value = opt.value;
        el.textContent = optionLabel(opt);
        if (opt.value === selectedValue) {
          el.selected = true;
        }
        select.appendChild(el);
      });
      select.disabled = options.length === 0;
    }

    function populateEducationLevel(keepSelection) {
      if (!educationType || !educationLevel) return;
      var stages = educationData.stages[educationType.value] || [];
      var selected = keepSelection ? educationLevel.dataset.initial || educationLevel.value : "";
      fillSelect(educationLevel, stages, lang === "bn" ? "নির্বাচন করুন" : "Select", selected);
      populateEducationClass(keepSelection);
    }

    function populateEducationClass(keepSelection) {
      if (!educationLevel || !educationClass || !educationClassField) return;
      var classes = educationData.classes[educationLevel.value] || [];
      if (classes.length === 0) {
        educationClassField.hidden = true;
        educationClass.value = "";
        return;
      }
      educationClassField.hidden = false;
      var selected = keepSelection ? educationClass.dataset.initial || educationClass.value : "";
      fillSelect(educationClass, classes, lang === "bn" ? "শ্রেণি নির্বাচন করুন" : "Select Class", selected);
    }

    function syncEducationDetail() {
      if (!educationDetailBlock) {
        return;
      }
      educationDetailBlock.hidden = !educationStatus || !educationStatus.value;
    }

    if (educationType) {
      populateEducationLevel(true);
      educationType.addEventListener("change", function () {
        populateEducationLevel(false);
      });
    }
    if (educationLevel) {
      educationLevel.addEventListener("change", function () {
        populateEducationClass(false);
      });
    }
    if (educationStatus) {
      syncEducationDetail();
      educationStatus.addEventListener("change", syncEducationDetail);
    }

    // ---- File upload widgets (drag & drop, preview, remove/replace) ----
    // Client-side size/extension checks run *before* the drop-zone accepts a
    // file, so users see the same error a server round-trip would produce
    // without ever losing their selection to a page reload.
    function validateFile(input, allowedExt, file) {
      file = file || (input.files && input.files[0]);
      if (!file) {
        clearError(input);
        return true;
      }
      if (file.size > MAX_FILE_BYTES) {
        fieldError(input, msg.fileSize);
        return false;
      }
      var ext = file.name.split(".").pop().toLowerCase();
      if (allowedExt && allowedExt.indexOf(ext) === -1) {
        fieldError(input, msg.fileType);
        return false;
      }
      clearError(input);
      return true;
    }

    if (window.ZarrahFileUpload) {
      var uploadFieldConfigs = {
        photo: ["jpg", "jpeg", "png", "webp"],
        identity_document: ["jpg", "jpeg", "png", "webp", "pdf"],
        cv: ["jpg", "jpeg", "png", "webp", "pdf"],
      };
      form.querySelectorAll("[data-upload-field]").forEach(function (wrapper) {
        var input = wrapper.querySelector('input[type="file"]');
        if (!input) return;
        var allowedExt = uploadFieldConfigs[input.name];
        window.ZarrahFileUpload.enhance(wrapper, {
          onSelect: function (file) {
            return validateFile(input, allowedExt, file);
          },
        });
      });
    }

    // ---- Live validation: names & phones ----
    function bindLiveValidation(id, regex, message) {
      var field = document.getElementById(id);
      if (!field) {
        return;
      }
      field.addEventListener("input", function () {
        var value = field.value.trim();
        if (!value) {
          clearError(field);
        } else if (!regex.test(value)) {
          fieldError(field, message);
        } else {
          fieldValid(field);
        }
      });
    }

    bindLiveValidation("id_bangla_name", BANGLA_NAME_RE, msg.bangla);
    bindLiveValidation("id_father_name", BANGLA_NAME_RE, msg.bangla);
    bindLiveValidation("id_mother_name", BANGLA_NAME_RE, msg.bangla);
    bindLiveValidation("id_english_name", ENGLISH_NAME_RE, msg.english);
    bindLiveValidation("id_phone", BD_PHONE_RE, msg.phone);
    bindLiveValidation("id_emergency_phone", BD_PHONE_RE, msg.phone);
    bindLiveValidation("id_email", EMAIL_RE, msg.email);
    bindLiveValidation("id_identity_number", NID_RE, msg.nid);

    // ---- Date of birth: Flatpickr (dd/mm/yyyy display, Y-m-d submit) ----
    // Progressive enhancement via date-picker.js. The hidden/original input
    // still holds Y-m-d for Django; age validation reads that same value.
    var dobField = document.getElementById("id_date_of_birth");
    var dobHint = document.querySelector("[data-dob-hint]");

    if (window.ZarrahDatePicker && dobField) {
      window.ZarrahDatePicker.enhance(dobField);
    }

    function validateDob() {
      if (!dobField) return true;
      if (!dobField.value) {
        clearError(dobField);
        return true;
      }
      var dob = new Date(dobField.value);
      var today = new Date();
      var age = today.getFullYear() - dob.getFullYear();
      var hadBirthdayThisYear =
        today.getMonth() > dob.getMonth() ||
        (today.getMonth() === dob.getMonth() && today.getDate() >= dob.getDate());
      if (!hadBirthdayThisYear) age -= 1;
      if (isNaN(dob.getTime()) || age < MIN_AGE) {
        fieldError(dobField, msg.age);
        return false;
      }
      fieldValid(dobField);
      return true;
    }

    if (dobField) {
      dobField.addEventListener("input", validateDob);
      dobField.addEventListener("change", validateDob);
      if (dobHint && dobField.dataset.datePickerReady === "true") {
        dobHint.hidden = true;
      }
      validateDob();
    }

    // ---- Required-field live validation on blur ----
    form.querySelectorAll("[aria-required='true']").forEach(function (field) {
      field.addEventListener("blur", function () {
        if (field.offsetParent === null) {
          return; // hidden section, skip
        }
        if (!field.value) {
          fieldError(field, msg.required);
        } else {
          fieldValid(field);
        }
      });
    });

    // ---- Submission: validate everything, then submit via fetch() so that
    // server-side validation errors can be applied to the existing DOM
    // in-place. Because the page never reloads on error, any file already
    // chosen in a file input (and its preview) survives — the browser only
    // clears file inputs on an actual navigation/reload, which this flow
    // avoids. If fetch is unavailable or fails outright, we fall back to a
    // normal (JS-free) form submission. ----
    function runFullClientValidation() {
      var firstInvalid = null;
      form.querySelectorAll("[aria-required='true']").forEach(function (field) {
        if (field.offsetParent === null) {
          return;
        }
        if (!field.value) {
          fieldError(field, msg.required);
          firstInvalid = firstInvalid || field;
        }
      });
      [
        ["id_bangla_name", BANGLA_NAME_RE, msg.bangla],
        ["id_father_name", BANGLA_NAME_RE, msg.bangla],
        ["id_mother_name", BANGLA_NAME_RE, msg.bangla],
        ["id_english_name", ENGLISH_NAME_RE, msg.english],
        ["id_phone", BD_PHONE_RE, msg.phone],
        ["id_emergency_phone", BD_PHONE_RE, msg.phone],
        ["id_email", EMAIL_RE, msg.email],
        ["id_identity_number", NID_RE, msg.nid],
      ].forEach(function (entry) {
        var field = document.getElementById(entry[0]);
        if (field && field.value && !entry[1].test(field.value.trim())) {
          fieldError(field, entry[2]);
          firstInvalid = firstInvalid || field;
        }
      });
      if (dobField && dobField.getAttribute("aria-invalid") === "true") {
        firstInvalid = firstInvalid || dobField;
      } else if (dobField && dobField.value) {
        if (!validateDob()) {
          firstInvalid = firstInvalid || dobField;
        }
      }
      return firstInvalid;
    }

    // ---- Validation summary banner ----
    // Mirrors the server-rendered #form-error-summary markup in apply.html
    // so the JS (fetch) submission path and a plain server round-trip look
    // identical. Field labels are read straight from each field's own
    // server-rendered <label> so the summary automatically matches whatever
    // language/label the page is already showing — no duplicated
    // translation logic needed here.
    var errorSummaryBox = document.getElementById("form-error-summary");
    var errorSummaryList = document.getElementById("form-error-summary-list");

    function labelFor(field) {
      var label = field.id && document.querySelector('label[for="' + field.id + '"]');
      if (!label) {
        return field.name || "";
      }
      // Strip the trailing " *" required-marker span's text, if any.
      var clone = label.cloneNode(true);
      var marker = clone.querySelector(".text-danger");
      if (marker) {
        marker.parentNode.removeChild(marker);
      }
      return clone.textContent.trim();
    }

    function hideErrorSummary() {
      if (!errorSummaryBox) return;
      errorSummaryBox.hidden = true;
      if (errorSummaryList) {
        errorSummaryList.innerHTML = "";
      }
    }

    // items: array of { field, message } (field optional — omit for a
    // form-wide, non-field-specific error) OR a single message string.
    function showErrorSummary(items) {
      if (!errorSummaryBox || !errorSummaryList) return;
      if (!items || (Array.isArray(items) && !items.length)) {
        hideErrorSummary();
        return;
      }
      if (typeof items === "string") {
        items = [{ message: items }];
      }

      errorSummaryList.innerHTML = "";
      items.forEach(function (item) {
        var li = document.createElement("li");
        if (item.field && item.field.id) {
          var link = document.createElement("a");
          link.href = "#" + item.field.id;
          link.textContent = labelFor(item.field);
          li.appendChild(link);
          li.appendChild(document.createTextNode(" — " + item.message));
        } else {
          li.textContent = item.message;
        }
        errorSummaryList.appendChild(li);
      });

      errorSummaryBox.hidden = false;
      errorSummaryBox.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    var submitBtn = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", function (event) {
      if (typeof window.fetch !== "function") {
        return; // no fetch support: let the normal multipart POST happen.
      }
      event.preventDefault();

      var firstInvalid = runFullClientValidation();
      if (firstInvalid) {
        showErrorSummary(msg.submitError);
        firstInvalid.focus();
        firstInvalid.scrollIntoView({ behavior: "smooth", block: "center" });
        return;
      }
      hideErrorSummary();

      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.dataset.originalText = submitBtn.innerHTML;
        submitBtn.innerHTML =
          '<span class="inline-flex items-center gap-2"><i class="bi bi-arrow-repeat" aria-hidden="true"></i>' +
          (lang === "bn" ? "জমা দেওয়া হচ্ছে..." : "Submitting...") +
          "</span>";
      }

      var formData = new FormData(form);
      fetch(form.action || window.location.href, {
        method: "POST",
        body: formData,
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin",
      })
        .then(function (response) {
          return response.json().then(function (data) {
            return { status: response.status, data: data };
          });
        })
        .then(function (result) {
          if (result.data.success) {
            window.location.href = result.data.redirect || "/membership/";
            return;
          }
          // Apply server-side field errors without touching the DOM nodes
          // for file inputs, so previews/selections stay intact.
          form.querySelectorAll(".form-error-js").forEach(function (el) {
            el.textContent = "";
          });
          var errors = result.data.errors || {};
          var firstErrField = null;
          var summaryItems = [];
          (result.data.non_field_errors || []).forEach(function (message) {
            summaryItems.push({ message: message });
          });
          Object.keys(errors).forEach(function (name) {
            if (name === "__all__") {
              return; // already covered by non_field_errors above
            }
            var field =
              document.getElementById("id_" + name) || form.querySelector('[name="' + name + '"]');
            var message = errors[name].join(" ");
            if (field) {
              fieldError(field, message);
              firstErrField = firstErrField || field;
              summaryItems.push({ field: field, message: message });
            } else {
              summaryItems.push({ message: message });
            }
          });
          showErrorSummary(summaryItems.length ? summaryItems : msg.submitError);
          if (firstErrField) {
            firstErrField.focus();
            firstErrField.scrollIntoView({ behavior: "smooth", block: "center" });
          }
        })
        .catch(function () {
          // Network/parse failure — degrade to a real submission so the
          // application isn't silently lost.
          showErrorSummary(msg.networkError);
          window.setTimeout(function () {
            HTMLFormElement.prototype.submit.call(form);
          }, 600);
        })
        .finally(function () {
          if (submitBtn) {
            submitBtn.disabled = false;
            if (submitBtn.dataset.originalText) {
              submitBtn.innerHTML = submitBtn.dataset.originalText;
            }
          }
        });
    });

    // ---- Section progress nav (active + completed states on scroll) ----
    var sectionNavLinks = document.querySelectorAll(".form-section-nav-link");
    var sections = document.querySelectorAll(".form-section");

    function markSectionDone(sectionId) {
      sectionNavLinks.forEach(function (link) {
        if (link.getAttribute("href") === "#" + sectionId) {
          link.classList.add("form-section-nav-link-done");
        }
      });
    }

    function sectionHasValue(section) {
      var controls = section.querySelectorAll("input, select, textarea");
      for (var i = 0; i < controls.length; i++) {
        var el = controls[i];
        if (el.type === "checkbox" || el.type === "radio") {
          if (el.checked) return true;
        } else if (el.type === "file") {
          if (el.files && el.files.length) return true;
        } else if (el.value && String(el.value).trim()) {
          return true;
        }
      }
      return false;
    }

    form.addEventListener("change", function () {
      sections.forEach(function (section) {
        if (sectionHasValue(section)) {
          markSectionDone(section.id);
        }
      });
    });

    if (sectionNavLinks.length && sections.length && "IntersectionObserver" in window) {
      var observer = new IntersectionObserver(
        function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              sectionNavLinks.forEach(function (link) {
                link.classList.toggle(
                  "form-section-nav-link-active",
                  link.getAttribute("href") === "#" + entry.target.id
                );
              });
            }
          });
        },
        { rootMargin: "-20% 0px -70% 0px" }
      );
      sections.forEach(function (section) {
        observer.observe(section);
        if (sectionHasValue(section)) {
          markSectionDone(section.id);
        }
      });
    }
  });
})();
