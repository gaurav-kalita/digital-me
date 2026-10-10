# Digital Me Autofill Extension

Manifest V3 Chrome extension that scans the active page, asks `ai-service` for a grounded fill plan, and applies the result to visible inputs.

## Structure

```text
browser-extension/
  manifest.json
  src/
    background/
    content/
    options/
    popup/
    shared/
  tests/
```

## How it works

1. The user clicks `Scan & Fill`.
2. The extension injects a content script into the active tab.
3. The content script scans visible fields and returns a normalized payload.
4. The background service worker calls the backend:
   - `POST /forms/plan` on `ai-service`
   - falls back to `POST /chat/` if the structured plan endpoint is unavailable
5. The content script applies the fill plan and highlights fields.

## Load unpacked

1. Open Chrome.
2. Go to `chrome://extensions`.
3. Enable `Developer mode`.
4. Click `Load unpacked`.
5. Select the `browser-extension/` folder.

## Backend configuration

The extension defaults to `http://127.0.0.1:8000`.

Adjust these in the extension `Settings` page if needed.

## Tests

Run the pure-function tests:

```bash
npm test
```

