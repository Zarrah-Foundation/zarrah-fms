/** @type {import('tailwindcss').Config} */
module.exports = {
  // static/js is included because a few interactive widgets (file upload,
  // mobile drawer, live validation) add/remove classes at runtime via
  // className strings rather than literal HTML — Tailwind's class scanner
  // needs to see those strings to avoid purging the matching CSS rules.
  //
  // form-input / form-select / form-textarea are applied by Django widgets
  // in *.forms.py (e.g. attrs={"class": "form-input"}), which are NOT in
  // `content` below. Classes defined inside `@layer components` are subject
  // to the same unused-class purge as utilities — if the scanner never sees
  // the class name, the entire rule is omitted from output.css. Safelist
  // keeps those design-system rules alive.
content: [
  "./templates/**/*.html",
  "./**/templates/**/*.html",
  "./static/js/**/*.js",
],
  safelist: [
    // Responsive display utilities used sparsely in page templates; without
    // safelist they can be missing from a stale/partial output.css build and
    // leave `hidden lg:block` permanently display:none (breaks CSS grids).
    "lg:block",
    "lg:flex",
    "lg:hidden",
    "lg:py-20",
    "lg:py-24",
    "xl:max-w-4xl",
    "form-input",
    "form-select",
    "form-textarea",
    // Dashboard stat cards / badges build these from a `tone` variable, so the
    // literal class names never appear in template source for the scanner.
    "text-primary-dark",
    "text-success",
    "text-warning",
    "text-danger",
    "text-info",
    "text-accent",
    "bg-primary/10",
    "bg-success/10",
    "bg-warning/10",
    "bg-danger/10",
    "bg-info/10",
    "bg-accent/10",
    "badge-primary",
    "badge-accent",
    "badge-success",
    "badge-warning",
    "badge-danger",
    "badge-info",
  ],
  theme: {
    container: {
      center: true,
      padding: "1rem",
    },
    extend: {
      colors: {
        primary: {
          DEFAULT: "#0B6B3A",
          dark: "#084F2C",
        },
        secondary: "#0F766E",
        accent: {
          DEFAULT: "#D4A017",
          light: "#EAB308",
        },
        surface: "#FFFFFF",
        canvas: "#F7F9F8",
        border: "#E5E7EB",
        ink: {
          DEFAULT: "#1F2937",
          light: "#6B7280",
        },
        success: "#16A34A",
        warning: "#F59E0B",
        danger: "#DC2626",
        info: "#2563EB",
      },
      fontFamily: {
        bn: ["Kalpurush", "Noto Sans Bengali", "sans-serif"],
        en: ["Manrope", "sans-serif"],
        sans: ["Manrope", "Kalpurush", "sans-serif"],
      },
      fontSize: {
        h1: ["56px", { lineHeight: "1.15", fontWeight: "700" }],
        h2: ["44px", { lineHeight: "1.2", fontWeight: "700" }],
        h3: ["34px", { lineHeight: "1.25", fontWeight: "600" }],
        h4: ["28px", { lineHeight: "1.3", fontWeight: "600" }],
        body: ["17px", { lineHeight: "1.7" }],
      },
      maxWidth: {
        app: "1400px",
      },
      borderRadius: {
        btn: "14px",
        field: "14px",
        card: "20px",
        nav: "24px",
        badge: "999px",
      },
      boxShadow: {
        "soft-sm": "0 4px 12px rgba(0,0,0,.06)",
        "soft-md": "0 10px 30px rgba(0,0,0,.10)",
        "soft-lg": "0 20px 60px rgba(0,0,0,.15)",
      },
      spacing: {
        "section-desktop": "80px",
        "section-tablet": "48px",
        "section-mobile": "32px",
      },
      transitionDuration: {
        DEFAULT: "250ms",
        200: "200ms",
        250: "250ms",
        300: "300ms",
      },
    },
  },
  plugins: [],
};
