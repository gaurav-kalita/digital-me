// frontend/lib/ai-service.js

const DEFAULT_BASE_URL = "http://127.0.0.1:8000";

function getAiServiceBaseUrl() {
  return process.env.AI_SERVICE_URL || DEFAULT_BASE_URL;
}

async function proxyResponse(upstreamResponse) {
  const contentType = upstreamResponse.headers.get("content-type") || "application/json";
  const body = await upstreamResponse.text();

  return new Response(body, {
    status: upstreamResponse.status,
    headers: {
      "content-type": contentType,
      "cache-control": "no-store",
    },
  });
}

export async function forwardJsonRequest(request, path) {
  const url = new URL(path, getAiServiceBaseUrl());
  const payload = await request.json();

  const upstreamResponse = await fetch(url, {
    method: request.method,
    headers: {
      "content-type": "application/json",
    },
    body: JSON.stringify(payload),
    cache: "no-store",
  });

  return proxyResponse(upstreamResponse);
}

export async function forwardGetRequest(request, path) {
  const url = new URL(path, getAiServiceBaseUrl());
  const upstreamResponse = await fetch(url, {
    method: request.method,
    cache: "no-store",
  });

  return proxyResponse(upstreamResponse);
}
