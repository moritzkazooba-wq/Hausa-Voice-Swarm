/**
 * Smoke test: single session via /test/simulate-call.
 *
 * Validates the endpoint is responding and p95 < 2000ms.
 * Run locally against docker-compose stack.
 */

import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  vus: 1,
  iterations: 5,
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    http_req_failed: ["rate<0.01"],
  },
};

export default function () {
  const payload = JSON.stringify({
    phone_number: "+2348012345678",
    text: "What is my account balance?",
  });

  const params = {
    headers: { "Content-Type": "application/json" },
    tags: { name: "simulate-call" },
  };

  const res = http.post(`${BASE_URL}/test/simulate-call`, payload, params);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "has response field": (r) => {
      const body = r.json();
      return body && body.response !== undefined;
    },
    "has session_id": (r) => {
      const body = r.json();
      return body && body.session_id !== undefined;
    },
    "has intent": (r) => {
      const body = r.json();
      return body && body.intent !== undefined;
    },
    "latency under 2s": (r) => r.timings.duration < 2000,
  });

  sleep(0.5);
}
