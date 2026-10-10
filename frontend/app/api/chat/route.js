// frontend/app/api/chat/route.js

import { forwardJsonRequest } from "../../../lib/ai-service";

export async function POST(request) {
  return forwardJsonRequest(request, "/chat/");
}
