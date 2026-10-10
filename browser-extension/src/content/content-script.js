// browser-extension/src/content/content-script.js

(function initializeAutofillContentScript() {
  if (window.__digitalMeAutofillInjected) {
    return;
  }
  window.__digitalMeAutofillInjected = true;

  const FIELD_ATTR = "data-digital-me-field-id";
  const FILLED_ATTR = "data-digital-me-filled";

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message || typeof message !== "object") {
      return false;
    }

    if (message.type === "SCAN_PAGE") {
      sendResponse(scanPage());
      return false;
    }

    if (message.type === "APPLY_FORM_PLAN") {
      sendResponse(applyFormPlan(message.plan || {}));
      return false;
    }

    return false;
  });

  function scanPage() {
    const fields = [];
    const candidates = collectFieldCandidates();

    candidates.forEach((entry, index) => {
      const { element } = entry;
      if (!isCandidateVisible(element) || isDisabled(element)) {
        return;
      }

      const fieldId = ensureFieldId(element, index);
      const field = describeField(element, fieldId, index);
      if (!field) {
        return;
      }

      fields.push({
        ...field,
        pageHints: {
          ...field.pageHints,
          context: entry.context,
          frame: entry.frameLabel,
        },
      });
    });

    return {
      site: extractSite(location.href),
      pageUrl: location.href,
      pageTitle: document.title || "",
      fields,
      scannedAt: new Date().toISOString(),
    };
  }

  function collectFieldCandidates() {
    const candidates = [];
    const seen = new WeakSet();
    const seenRoots = new WeakSet();

    collectFromRoot(document, candidates, seen, seenRoots, "top-level document");
    collectSameOriginFrames(document, candidates, seen, seenRoots);

    return candidates;
  }

  function collectFromRoot(root, candidates, seen, seenRoots, frameLabel) {
    if (seenRoots.has(root)) {
      return;
    }
    seenRoots.add(root);

    const selector = "input, textarea, select, [contenteditable='true'], [role='textbox']";
    const elements = Array.from(root.querySelectorAll(selector));

    elements.forEach((element) => {
      if (seen.has(element)) {
        return;
      }

      seen.add(element);
      candidates.push({
        element,
        frameLabel,
        context: collectPageHints(element),
      });

      const shadowRoot = element.shadowRoot;
      if (shadowRoot && !seenRoots.has(shadowRoot)) {
        collectFromRoot(shadowRoot, candidates, seen, seenRoots, `${frameLabel} > shadow-root`);
      }
    });
  }

  function collectSameOriginFrames(root, candidates, seen, seenRoots) {
    const frames = Array.from(root.querySelectorAll("iframe"));
    frames.forEach((frame, index) => {
      let frameDocument = null;
      try {
        frameDocument = frame.contentDocument;
      } catch {
        frameDocument = null;
      }

      if (!frameDocument) {
        return;
      }

      const frameLabel = frame.getAttribute("title") || frame.getAttribute("name") || `iframe-${index}`;
      collectFromRoot(frameDocument, candidates, seen, seenRoots, frameLabel);
      collectSameOriginFrames(frameDocument, candidates, seen, seenRoots);
    });
  }

  function applyFormPlan(plan) {
    const actions = Array.isArray(plan.actions) ? plan.actions : [];
    const policy = plan.policy || {};
    const summary = {
      filled: 0,
      skipped: 0,
      missing: 0,
      highRiskSkipped: 0,
    };

    for (const action of actions) {
      const fieldId = String(action.field_id || action.fieldId || "").trim();
      if (!fieldId) {
        summary.missing += 1;
        continue;
      }

      const element = document.querySelector(`[${FIELD_ATTR}="${CSS.escape(fieldId)}"]`);
      if (!element) {
        summary.missing += 1;
        continue;
      }

      const risk = String(action.risk || "low").toLowerCase();
      const shouldFill = String(action.action || "fill").toLowerCase() === "fill";
      if (!shouldFill) {
        summary.skipped += 1;
        markField(element, "skip", policy);
        continue;
      }

      if (risk === "high" && !policy.autoFillHighRisk) {
        summary.highRiskSkipped += 1;
        markField(element, "high-risk", policy);
        continue;
      }

      const applied = fillElement(element, action.value);
      markField(element, applied ? "filled" : "failed", policy);
      if (applied) {
        summary.filled += 1;
      } else {
        summary.skipped += 1;
      }
    }

    return {
      ok: true,
      summary,
      updatedAt: new Date().toISOString(),
    };
  }

  function ensureFieldId(element, index) {
    const existing = element.getAttribute(FIELD_ATTR);
    if (existing) {
      return existing;
    }

    const parts = [
      element.id,
      element.name,
      element.getAttribute("aria-label"),
      element.getAttribute("placeholder"),
      element.type,
      element.tagName.toLowerCase(),
      String(index),
    ].filter(Boolean);
    const fieldId = slugify(parts.join("-")) || `field-${index}`;
    element.setAttribute(FIELD_ATTR, fieldId);
    return fieldId;
  }

  function describeField(element, fieldId, index) {
    const fieldType = getFieldType(element);
    if (fieldType === "button" || fieldType === "submit") {
      return null;
    }

    const label = getFieldLabel(element);
    const name = element.name || "";
    const placeholder = element.getAttribute("placeholder") || "";
    const ariaLabel = element.getAttribute("aria-label") || "";
    const autocomplete = element.getAttribute("autocomplete") || "";
    const currentValue = getCurrentValue(element);
    const options = getOptions(element);
    const pageHints = collectPageHints(element);
    const risk = classifyFieldRisk({
      label,
      name,
      placeholder,
      autocomplete,
      ariaLabel,
      fieldType,
      tagName: element.tagName.toLowerCase(),
    });

    return {
      fieldId,
      label,
      fieldType,
      tagName: element.tagName.toLowerCase(),
      name,
      placeholder,
      autocomplete,
      ariaLabel,
      currentValue,
      required: element.required || false,
      visible: true,
      disabled: false,
      options,
      risk,
      pageHints: {
        index,
        context: pageHints,
      },
    };
  }

  function fillElement(element, value) {
    const nextValue = value == null ? "" : String(value);
    if (element.tagName.toLowerCase() === "select") {
      return fillSelect(element, nextValue);
    }

    if (element.isContentEditable) {
      element.focus();
      element.textContent = nextValue;
      dispatchChange(element);
      return true;
    }

    if ("value" in element) {
      element.focus();
      const prototype = Object.getPrototypeOf(element);
      const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
      if (valueSetter) {
        valueSetter.call(element, nextValue);
      } else {
        element.value = nextValue;
      }
      dispatchChange(element);
      return true;
    }

    return false;
  }

  function fillSelect(selectElement, value) {
    const normalizedValue = normalizeWhitespace(value).toLowerCase();
    const options = Array.from(selectElement.options || []);
    const matchedOption = options.find((option) => {
      const optionValue = normalizeWhitespace(option.value).toLowerCase();
      const optionLabel = normalizeWhitespace(option.label || option.textContent).toLowerCase();
      return optionValue === normalizedValue || optionLabel === normalizedValue;
    });

    if (!matchedOption) {
      return false;
    }

    selectElement.value = matchedOption.value;
    dispatchChange(selectElement);
    return true;
  }

  function dispatchChange(element) {
    element.dispatchEvent(new InputEvent("input", { bubbles: true, composed: true }));
    element.dispatchEvent(new Event("change", { bubbles: true, composed: true }));
    element.setAttribute(FILLED_ATTR, "true");
  }

  function markField(element, state, policy) {
    if (policy && policy.highlightFilledFields === false) {
      return;
    }

    const styles = {
      filled: "2px solid #2f9e44",
      skip: "2px solid #f08c00",
      "high-risk": "2px solid #e03131",
      failed: "2px solid #c92a2a",
    };

    element.style.outline = styles[state] || styles.failed;
    element.style.outlineOffset = "2px";
    element.setAttribute(FILLED_ATTR, state);
  }

  function getFieldLabel(element) {
    const ariaLabel = element.getAttribute("aria-label");
    if (ariaLabel) {
      return normalizeWhitespace(ariaLabel);
    }

    const labelledBy = element.getAttribute("aria-labelledby");
    if (labelledBy) {
      const parts = labelledBy
        .split(/\s+/)
        .map((id) => document.getElementById(id))
        .filter(Boolean)
        .map((node) => normalizeWhitespace(node.textContent));
      if (parts.length > 0) {
        return parts.join(" ");
      }
    }

    if (element.id) {
      const label = document.querySelector(`label[for="${CSS.escape(element.id)}"]`);
      if (label) {
        return normalizeWhitespace(label.textContent);
      }
    }

    const closestLabel = element.closest("label");
    if (closestLabel) {
      return normalizeWhitespace(closestLabel.textContent);
    }

    const container = element.closest("div, li, td, th, fieldset, section, article");
    if (container) {
      const text = normalizeWhitespace(container.textContent);
      if (text.length > 0 && text.length < 160) {
        return text;
      }
    }

    return element.getAttribute("placeholder") || element.name || element.id || "";
  }

  function collectPageHints(element) {
    const parent = element.parentElement;
    if (!parent) {
      return "";
    }

    const text = normalizeWhitespace(parent.textContent);
    return text.length > 160 ? text.slice(0, 160) : text;
  }

  function getOptions(element) {
    if (element.tagName.toLowerCase() !== "select") {
      return [];
    }

    return Array.from(element.options || [])
      .map((option) => normalizeWhitespace(option.label || option.textContent || option.value))
      .filter(Boolean)
      .slice(0, 25);
  }

  function getFieldType(element) {
    const tag = element.tagName.toLowerCase();
    if (tag === "textarea") {
      return "textarea";
    }
    if (tag === "select") {
      return "select";
    }
    if (element.isContentEditable) {
      return "contenteditable";
    }
    return normalizeWhitespace(element.type || "text").toLowerCase();
  }

  function getCurrentValue(element) {
    if (element.tagName.toLowerCase() === "select") {
      const option = element.options?.[element.selectedIndex];
      return option ? normalizeWhitespace(option.label || option.textContent || option.value) : "";
    }
    if (element.isContentEditable) {
      return normalizeWhitespace(element.textContent);
    }
    return normalizeWhitespace(element.value || "");
  }

  function isCandidateVisible(element) {
    const rect = element.getBoundingClientRect();
    const styles = window.getComputedStyle(element);
    return (
      rect.width > 0 &&
      rect.height > 0 &&
      styles.visibility !== "hidden" &&
      styles.display !== "none" &&
      styles.opacity !== "0"
    );
  }

  function isDisabled(element) {
    return Boolean(element.disabled || element.readOnly || element.getAttribute("aria-disabled") === "true");
  }

  function extractSite(pageUrl) {
    try {
      return new URL(pageUrl).hostname.replace(/^www\./i, "");
    } catch {
      return "unknown-site";
    }
  }

  function normalizeWhitespace(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function slugify(value) {
    return normalizeWhitespace(value)
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "");
  }

  function classifyFieldRisk(field) {
    const haystack = normalizeWhitespace(
      [field.label, field.name, field.placeholder, field.autocomplete, field.ariaLabel, field.fieldType, field.tagName]
        .filter(Boolean)
        .join(" ")
    ).toLowerCase();

    const sensitivePatterns = [
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

    const highValuePatterns = [
      "salary",
      "current salary",
      "expected salary",
      "ctc",
      "notice period",
      "current ctc",
      "employment type",
      "relocation",
    ];

    if (field.fieldType === "password" || sensitivePatterns.some((pattern) => haystack.includes(pattern))) {
      return "high";
    }

    if (highValuePatterns.some((pattern) => haystack.includes(pattern))) {
      return "medium";
    }

    return "low";
  }
})();
