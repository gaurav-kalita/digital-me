// browser-extension/src/options/options.js

import { DEFAULT_SETTINGS } from "../shared/constants.js";
import { loadSettings, saveSettings } from "../shared/storage.js";

const form = document.getElementById("settingsForm");
const resetButton = document.getElementById("resetButton");

const fields = {
  primaryBackendUrl: document.getElementById("primaryBackendUrl"),
  fallbackBackendUrl: document.getElementById("fallbackBackendUrl"),
  autoFillHighRisk: document.getElementById("autoFillHighRisk"),
  highlightFilledFields: document.getElementById("highlightFilledFields"),
  requestTimeoutMs: document.getElementById("requestTimeoutMs"),
};

await loadIntoForm();

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  await saveSettings(readForm());
  flashButton(form.querySelector("button[type='submit']"), "Saved");
});

resetButton.addEventListener("click", async () => {
  await saveSettings(DEFAULT_SETTINGS);
  await loadIntoForm();
  flashButton(resetButton, "Reset");
});

async function loadIntoForm() {
  const settings = await loadSettings();
  fields.primaryBackendUrl.value = settings.primaryBackendUrl;
  fields.fallbackBackendUrl.value = settings.fallbackBackendUrl;
  fields.autoFillHighRisk.checked = Boolean(settings.autoFillHighRisk);
  fields.highlightFilledFields.checked = Boolean(settings.highlightFilledFields);
  fields.requestTimeoutMs.value = String(settings.requestTimeoutMs);
}

function readForm() {
  return {
    primaryBackendUrl: fields.primaryBackendUrl.value.trim(),
    fallbackBackendUrl: fields.fallbackBackendUrl.value.trim(),
    autoFillHighRisk: fields.autoFillHighRisk.checked,
    highlightFilledFields: fields.highlightFilledFields.checked,
    requestTimeoutMs: Number(fields.requestTimeoutMs.value || DEFAULT_SETTINGS.requestTimeoutMs),
  };
}

function flashButton(button, label) {
  const original = button.textContent;
  button.textContent = label;
  window.setTimeout(() => {
    button.textContent = original;
  }, 1000);
}

