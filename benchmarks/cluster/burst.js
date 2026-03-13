/**
 * REQUIRES GKE
 *
 * Burst test: spike from 10→100 sessions in 2 minutes.
 *
 * Validates system behavior under sudden traffic spikes.
 * Tests HPA rapid scale-up and request queuing.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { randomUtterance } from "../utterances.js";

const BASE_URL = __ENV.BASE_URL || "http://voice-pipeline.hausa-voice-swarm.svc:8000";

export const options = {
  stages: [
    { duration: "30s", target: 10 },   // Warm up
    { duration: "15s", target: 100 },   // Spike
    { duration: "1m", target: 100 },    // Hold peak
    { duration: "15s", target: 10 },    // Drop
  ],
  thresholds: {
    http_req_duration: ["p(95)<3000"],
    http_req_failed: ["rate<0.05"],
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
  const { text } = randomUtterance();
  const res = simulateCall(text);

  check(res, {
    "status is 200": (r) => r.status === 200,
    "response under 3s": (r) => r.timings.duration < 3000,
  });

  sleep(0.5 + Math.random());
}
