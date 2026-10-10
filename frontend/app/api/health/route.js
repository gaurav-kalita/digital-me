// frontend/app/api/health/route.js

import { forwardGetRequest } from "../../../lib/ai-service";

export async function GET(request) {
  return forwardGetRequest(request, "/health/");
}
