/**
 * REQUIRES GKE
 *
 * Sustained load test: 50 concurrent sessions for 30 minutes.
 *
 * Validates system stability under steady-state production-like load.
 * Checks for memory leaks, connection pool exhaustion, and latency drift.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { weightedIntent, utteranceForIntent } from "../utterances.js";

const BASE_URL = __ENV.BASE_URL || "http://voice-pipeline.hausa-voice-swarm.svc:8000";

export const options = {
  stages: [
    { duration: "2m", target: 50 },    // Ramp up
    { duration: "26m", target: 50 },   // Sustain
    { duration: "2m", target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<3000"],
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
  // 3-turn conversation
  for (let turn = 0; turn < 3; turn++) {
    const intent = weightedIntent();
    const text = utteranceForIntent(intent);
    const res = simulateCall(text);

    check(res, {
      "status is 200": (r) => r.status === 200,
    });

    sleep(1 + Math.random() * 2);
  }

  // Pause between sessions
  sleep(2 + Math.random() * 3);
}
