// browser-extension/src/popup/popup.js

import { loadLastRun } from "../shared/storage.js";

const runButton = document.getElementById("runButton");
const settingsButton = document.getElementById("settingsButton");
const statusElement = document.getElementById("status");
const lastRunElement = document.getElementById("lastRun");

runButton.addEventListener("click", runAutofill);
settingsButton.addEventListener("click", openSettings);

await renderLastRun();

async function runAutofill() {
  setStatus("Scanning current page...");
  runButton.disabled = true;

  try {
    const result = await sendMessage({ type: "AUTOFILL_ACTIVE_TAB" });
    const payload = result.payload;
    const scanned = payload?.scan?.fields?.length || 0;
    const filled = payload?.applyResult?.summary?.filled || 0;
    const skipped = payload?.applyResult?.summary?.skipped || 0;
    const highRiskSkipped = payload?.applyResult?.summary?.highRiskSkipped || 0;

    setStatus(
      `Completed. Scanned ${scanned} fields. Filled ${filled} fields, skipped ${skipped}. High-risk skipped: ${highRiskSkipped}.`
    );
    await renderLastRun();
  } catch (error) {
    setStatus(error.message || "Autofill failed.");
  } finally {
    runButton.disabled = false;
  }
}

function openSettings() {
  chrome.runtime.openOptionsPage();
}

function sendMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      const error = chrome.runtime.lastError;
      if (error) {
        reject(new Error(error.message));
        return;
      }

      if (!response?.ok) {
        reject(new Error(response?.error?.message || "Unknown extension error"));
        return;
      }

      resolve(response);
    });
  });
}

async function renderLastRun() {
  const lastRun = await loadLastRun();
  if (!lastRun) {
    lastRunElement.textContent = "No run yet.";
    return;
  }

  lastRunElement.textContent = JSON.stringify(
    {
      site: lastRun.plan?.site || lastRun.scan?.site || "unknown",
      scanned: lastRun.scan?.fields?.length || 0,
      filled: lastRun.applyResult?.summary?.filled || 0,
      skipped: lastRun.applyResult?.summary?.skipped || 0,
      highRiskSkipped: lastRun.applyResult?.summary?.highRiskSkipped || 0,
      updatedAt: lastRun.completedAt,
    },
    null,
    2
  );
}

function setStatus(text) {
  statusElement.textContent = text;
}
