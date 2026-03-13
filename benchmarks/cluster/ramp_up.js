/**
 * REQUIRES GKE
 *
 * Ramp-up test: 1→50 sessions over 10 minutes.
 *
 * Validates HPA scaling behavior and latency under increasing load.
 * Target: p95 < 2000ms, error rate < 1%.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { randomUtterance, weightedIntent, utteranceForIntent } from "../utterances.js";

const BASE_URL = __ENV.BASE_URL || "http://voice-pipeline.hausa-voice-swarm.svc:8000";

export const options = {
  stages: [
    { duration: "2m", target: 10 },
    { duration: "3m", target: 25 },
    { duration: "3m", target: 50 },
    { duration: "2m", target: 50 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000"],
    http_req_failed: ["rate<0.01"],
  },
};

function simulateCall(text) {
  const payload = JSON.stringify({
    phone_number: "+2348012345678",
    text: text,
  });
  const params = {
    headers: { "Content-Type": "application/json" },
    tags: { name: "simulate-call" },
  };
  return http.post(`${BASE_URL}/test/simulate-call`, payload, params);
}

export default function () {
  const intent = weightedIntent();
  const text = utteranceForIntent(intent);
  const res = simulateCall(text);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "has response": (r) => r.json() && r.json().response !== undefined,
  });

  sleep(1 + Math.random() * 3);
}
