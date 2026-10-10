import assert from "node:assert/strict";

import {
  buildChatQuestion,
  buildFieldQuestion,
  classifyFieldRisk,
  enrichFieldForBackend,
  extractSiteFromUrl,
  normalizeWhitespace,
} from "../src/shared/field-utils.js";

assert.equal(normalizeWhitespace("  Gaurav   Kalita  "), "Gaurav Kalita");
assert.equal(extractSiteFromUrl("https://www.naukri.com/profile"), "naukri.com");
assert.equal(classifyFieldRisk({ label: "Password", fieldType: "password" }), "high");
assert.equal(classifyFieldRisk({ label: "Notice Period", fieldType: "text" }), "medium");

const question = buildFieldQuestion(
  { site: "naukri", pageUrl: "https://naukri.com", pageTitle: "Profile" },
  { fieldId: "full_name", label: "Full Name", name: "name", fieldType: "text", currentValue: "" }
);

assert.match(question, /naukri/);
assert.match(question, /Full Name/);

const chatQuestion = buildChatQuestion(
  {
    site: "naukri.com",
    pageUrl: "https://naukri.com/profile",
    pageTitle: "Profile",
  },
  {
    fieldId: "notice_period",
    label: "Notice Period",
    fieldType: "text",
    currentValue: "",
  }
);

assert.ok(chatQuestion.length <= 480);
assert.match(chatQuestion, /Return only the exact value/);

const payload = enrichFieldForBackend(
  {
    fieldId: "notice_period",
    label: "Notice Period",
    fieldType: "text",
    tagName: "input",
    name: "notice_period",
    currentValue: "",
  },
  2
);

assert.equal(payload.field_id, "notice_period");
assert.equal(payload.page_hints.index, 2);
assert.equal(payload.page_hints.risk, "medium");

console.log("browser-extension smoke tests passed");
