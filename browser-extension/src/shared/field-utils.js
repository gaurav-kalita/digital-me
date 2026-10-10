// browser-extension/src/shared/field-utils.js

import { FIELD_RISK } from "./constants.js";

const SENSITIVE_PATTERNS = [
  "password",
  "passcode",
  "otp",
  "one time password",
  "cvv",
  "pan",
  "aadhaar",
  "aadhar",
  "ssn",
  "social security",
  "bank",
  "account number",
  "routing",
  "credit card",
  "debit card",
  "upi pin",
  "pin",
];

const HIGH_VALUE_PATTERNS = [
  "salary",
  "current salary",
  "expected salary",
  "ctc",
  "notice period",
  "current ctc",
  "employment type",
  "relocation",
];

const MEDIUM_VALUE_PATTERNS = [
  "email",
  "phone",
  "mobile",
  "linkedin",
  "github",
  "portfolio",
  "website",
  "url",
  "profile",
  "summary",
  "headline",
  "experience",
  "education",
  "skills",
];

const CHAT_QUESTION_MAX_LENGTH = 480;

export function normalizeWhitespace(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

export function extractSiteFromUrl(pageUrl) {
  try {
    const url = new URL(pageUrl);
    return url.hostname.replace(/^www\./i, "");
  } catch {
    return "unknown-site";
  }
}

export function classifyFieldRisk(field) {
  const haystack = normalizeWhitespace(
    [
      field.label,
      field.name,
      field.placeholder,
      field.autocomplete,
      field.ariaLabel,
      field.fieldType,
      field.tagName,
    ]
      .filter(Boolean)
      .join(" ")
  ).toLowerCase();

  if (field.fieldType === "password" || SENSITIVE_PATTERNS.some((pattern) => haystack.includes(pattern))) {
    return FIELD_RISK.high;
  }

  if (HIGH_VALUE_PATTERNS.some((pattern) => haystack.includes(pattern))) {
    return FIELD_RISK.medium;
  }

  if (MEDIUM_VALUE_PATTERNS.some((pattern) => haystack.includes(pattern))) {
    return FIELD_RISK.low;
  }

  return FIELD_RISK.low;
}

export function shouldSkipField(field) {
  const risk = classifyFieldRisk(field);
  return risk === FIELD_RISK.high && field.fieldType === "password";
}

export function buildFieldQuestion(scanContext, field) {
  const fieldSummary = [
    `label=${field.label || "n/a"}`,
    `name=${field.name || "n/a"}`,
    `placeholder=${field.placeholder || "n/a"}`,
    `autocomplete=${field.autocomplete || "n/a"}`,
    `aria=${field.ariaLabel || "n/a"}`,
    `type=${field.fieldType || "n/a"}`,
    `current=${field.currentValue || "empty"}`,
  ].join(", ");

  return [
    `Fill the field "${field.label || field.name || field.fieldId}" for the site ${scanContext.site}.`,
    `Page title: ${scanContext.pageTitle || "unknown"}.`,
    `Page URL: ${scanContext.pageUrl}.`,
    `Field details: ${fieldSummary}.`,
    "Return the exact value only, no prose.",
  ].join(" ");
}

export function enrichFieldForBackend(field, index) {
  return {
    field_id: field.fieldId,
    label: field.label || "",
    field_type: field.fieldType || "",
    tag_name: field.tagName || "",
    name: field.name || "",
    placeholder: field.placeholder || "",
    autocomplete: field.autocomplete || "",
    aria_label: field.ariaLabel || "",
    current_value: field.currentValue || "",
    required: Boolean(field.required),
    visible: Boolean(field.visible),
    disabled: Boolean(field.disabled),
    options: Array.isArray(field.options) ? field.options : [],
    page_hints: {
      index,
      risk: classifyFieldRisk(field),
    },
  };
}

function truncateText(value, maxLength) {
  const text = normalizeWhitespace(value);
  if (text.length <= maxLength) {
    return text;
  }

  return `${text.slice(0, Math.max(0, maxLength - 3)).trimEnd()}...`;
}

export function buildChatQuestion(scanContext, field) {
  const fieldName = field.label || field.name || field.fieldId || "this field";
  const site = scanContext.site || "this site";
  const fieldType = field.fieldType ? ` ${field.fieldType}` : "";
  const question = `What value should be entered in the "${fieldName}"${fieldType} field on ${site}? Return only the exact value.`;

  return truncateText(question, CHAT_QUESTION_MAX_LENGTH);
}
