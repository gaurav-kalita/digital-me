// browser-extension/src/shared/storage.js

import { DEFAULT_SETTINGS, STORAGE_KEYS } from "./constants.js";

export async function loadSettings() {
  const result = await chrome.storage.local.get([STORAGE_KEYS.settings]);
  return {
    ...DEFAULT_SETTINGS,
    ...(result[STORAGE_KEYS.settings] || {}),
  };
}

export async function saveSettings(settings) {
  await chrome.storage.local.set({
    [STORAGE_KEYS.settings]: {
      ...DEFAULT_SETTINGS,
      ...settings,
    },
  });
}

export async function saveLastRun(payload) {
  await chrome.storage.session.set({
    [STORAGE_KEYS.lastRun]: payload,
  });
}

export async function loadLastRun() {
  const result = await chrome.storage.session.get([STORAGE_KEYS.lastRun]);
  return result[STORAGE_KEYS.lastRun] || null;
}

