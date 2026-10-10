// browser-extension/src/shared/backend-client.js

import { API_PATHS } from "./constants.js";
import { buildChatQuestion, enrichFieldForBackend } from "./field-utils.js";

async function fetchJson(url, init, timeoutMs) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(new Error("Request timed out")), timeoutMs);

  try {
    const response = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        "content-type": "application/json",
        ...(init?.headers || {}),
      },
    });

    const text = await response.text();
    let payload = null;
    try {
      payload = text ? JSON.parse(text) : null;
    } catch {
      payload = { raw: text };
    }

    return { response, payload };
  } finally {
    clearTimeout(timer);
  }
}

function normalizePlanResponse(payload, scanContext) {
  if (!payload || typeof payload !== "object") {
    return buildChatFallbackPlan(scanContext, []);
  }

  const actions = Array.isArray(payload.actions) ? payload.actions : [];
  return {
    site: payload.site || scanContext.site,
    page_url: payload.page_url || scanContext.pageUrl,
    page_title: payload.page_title || scanContext.pageTitle,
    actions,
    skipped: Array.isArray(payload.skipped) ? payload.skipped : [],
    metadata: payload.metadata || {},
  };
}

async function requestFormPlan(baseUrl, scanContext, settings) {
  const url = new URL(API_PATHS.formPlan, baseUrl);
  const body = {
    site: scanContext.site,
    page_url: scanContext.pageUrl,
    page_title: scanContext.pageTitle,
    fields: scanContext.fields.map(enrichFieldForBackend),
  };

  const { response, payload } = await fetchJson(
    url,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
    settings.requestTimeoutMs
  );

  if (!response.ok) {
    const error = new Error(`Form plan request failed with status ${response.status}`);
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  return normalizePlanResponse(payload, scanContext);
}

async function requestChatFallback(baseUrl, scanContext, settings) {
  const actions = [];

  for (const field of scanContext.fields) {
    const question = buildChatQuestion(scanContext, field);
    const { response, payload } = await fetchJson(
      new URL(API_PATHS.chat, baseUrl),
      {
        method: "POST",
        body: JSON.stringify({ question }),
      },
      settings.requestTimeoutMs
    );

    if (!response.ok) {
      actions.push({
        field_id: field.fieldId,
        action: "skip",
        value: "",
        confidence: 0,
        risk: "medium",
        reason: `Chat fallback failed with status ${response.status}`,
        source_labels: [],
        matched_field: "",
      });
      continue;
    }

    actions.push({
      field_id: field.fieldId,
      action: "fill",
      value: extractValueFromChatResponse(payload?.answer || payload?.raw || ""),
      confidence: 0.58,
      risk: field.risk,
      reason: "Derived from grounded chat response",
      source_labels: payload?.sources || [],
      matched_field: field.label || field.name || field.fieldId,
    });
  }

  return {
    site: scanContext.site,
    page_url: scanContext.pageUrl,
    page_title: scanContext.pageTitle,
    actions,
    skipped: actions.filter((action) => action.action !== "fill").map((action) => action.field_id),
    metadata: {
      mode: "chat-fallback",
      source: baseUrl,
    },
  };
}

function buildChatFallbackPlan(scanContext, actions) {
  return {
    site: scanContext.site,
    page_url: scanContext.pageUrl,
    page_title: scanContext.pageTitle,
    actions,
    skipped: [],
    metadata: {
      mode: "empty",
    },
  };
}

function extractValueFromChatResponse(answer) {
  const text = String(answer || "").trim();
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  return lines[0] || text;
}

export async function buildFormPlan(scanContext, settings) {
  const primaryUrl = settings.primaryBackendUrl;
  const fallbackUrl = settings.fallbackBackendUrl;
  const attempted = [];

  for (const baseUrl of [primaryUrl, fallbackUrl].filter(Boolean)) {
    attempted.push(baseUrl);
    try {
      return await requestFormPlan(baseUrl, scanContext, settings);
    } catch (error) {
      if (error.status && error.status !== 404 && error.status !== 405) {
        continue;
      }
    }
  }

  for (const baseUrl of [primaryUrl, fallbackUrl].filter(Boolean)) {
    if (attempted.includes(baseUrl)) {
      try {
        return await requestChatFallback(baseUrl, scanContext, settings);
      } catch {
        // Keep trying remaining backends.
      }
    }
  }

  return {
    site: scanContext.site,
    page_url: scanContext.pageUrl,
    page_title: scanContext.pageTitle,
    actions: [],
    skipped: scanContext.fields.map((field) => field.fieldId),
    metadata: {
      mode: "unavailable",
      attempted,
    },
  };
}
