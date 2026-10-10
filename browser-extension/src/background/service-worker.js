// browser-extension/src/background/service-worker.js

import { buildFormPlan } from "../shared/backend-client.js";
import { DEFAULT_SETTINGS, STORAGE_KEYS } from "../shared/constants.js";
import { loadLastRun, loadSettings, saveLastRun, saveSettings } from "../shared/storage.js";

chrome.runtime.onInstalled.addListener(async () => {
  const existing = await chrome.storage.local.get([STORAGE_KEYS.settings]);
  if (!existing[STORAGE_KEYS.settings]) {
    await saveSettings(DEFAULT_SETTINGS);
  }
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (!message || typeof message !== "object") {
    return false;
  }

  if (message.type === "AUTOFILL_ACTIVE_TAB") {
    handleAutofillRequest()
      .then((payload) => sendResponse({ ok: true, payload }))
      .catch((error) => sendResponse({ ok: false, error: serializeError(error) }));
    return true;
  }

  if (message.type === "GET_LAST_RUN") {
    loadLastRun()
      .then((payload) => sendResponse({ ok: true, payload }))
      .catch((error) => sendResponse({ ok: false, error: serializeError(error) }));
    return true;
  }

  return false;
});

async function handleAutofillRequest() {
  const tab = await getActiveTab();
  if (!tab?.id) {
    throw new Error("No active tab found");
  }

  await ensureContentScript(tab.id);

  const scan = await sendTabMessage(tab.id, { type: "SCAN_PAGE" });
  if (!scan || !Array.isArray(scan.fields) || scan.fields.length === 0) {
    throw new Error("No fillable fields were found on the current page");
  }

  const settings = await loadSettings();
  const plan = await buildFormPlan(scan, settings);
  const applyResult = await sendTabMessage(tab.id, {
    type: "APPLY_FORM_PLAN",
    plan: {
      ...plan,
      policy: {
        autoFillHighRisk: Boolean(settings.autoFillHighRisk),
        highlightFilledFields: Boolean(settings.highlightFilledFields),
      },
    },
  });

  const payload = {
    scan,
    plan,
    applyResult,
    completedAt: new Date().toISOString(),
  };

  await saveLastRun(payload);
  await updateBadge(applyResult?.summary?.filled || 0);
  return payload;
}

async function getActiveTab() {
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  return tabs[0] || null;
}

async function ensureContentScript(tabId) {
  await chrome.scripting.executeScript({
    target: { tabId },
    files: ["src/content/content-script.js"],
  });
}

function sendTabMessage(tabId, message) {
  return new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
        return;
      }
      resolve(response);
    });
  });
}

async function updateBadge(count) {
  await chrome.action.setBadgeBackgroundColor({ color: "#2f9e44" });
  await chrome.action.setBadgeText({ text: count > 0 ? String(count) : "" });
}

function serializeError(error) {
  return {
    message: error?.message || String(error),
    status: error?.status || 0,
  };
}
