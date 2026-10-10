// browser-extension/src/shared/constants.js

export const STORAGE_KEYS = {
  settings: "digitalMeAutofillSettings",
  lastRun: "digitalMeAutofillLastRun",
};

export const DEFAULT_SETTINGS = {
  primaryBackendUrl: "http://127.0.0.1:8000",
  fallbackBackendUrl: "http://127.0.0.1:8000",
  autoFillHighRisk: false,
  highlightFilledFields: true,
  requestTimeoutMs: 12000,
};

export const API_PATHS = {
  formPlan: "/forms/plan",
  chat: "/chat/",
};

export const FIELD_RISK = {
  low: "low",
  medium: "medium",
  high: "high",
};

