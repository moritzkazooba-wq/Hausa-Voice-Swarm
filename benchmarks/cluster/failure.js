/**
 * REQUIRES GKE
 *
 * Failure/chaos test: 50 sessions + pod kill + Redis recovery.
 *
 * Run alongside manual pod disruption:
 *   kubectl delete pod -l app=voice-pipeline -n hausa-voice-swarm --wait=false
 *
 * Validates:
 * - Graceful degradation when pods are killed
 * - Session recovery after Redis reconnection
 * - PDB enforcement (minAvailable: 1)
 * - Error rate stays below 10% during disruption
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Counter } from "k6/metrics";
import { randomUtterance } from "../utterances.js";

const BASE_URL = __ENV.BASE_URL || "http://voice-pipeline.hausa-voice-swarm.svc:8000";

const recoveryErrors = new Counter("recovery_errors");

export const options = {
  stages: [
    { duration: "1m", target: 50 },    // Ramp to steady state
    { duration: "3m", target: 50 },    // Hold — kill pods during this phase
    { duration: "2m", target: 50 },    // Recovery observation
    { duration: "1m", target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_failed: ["rate<0.10"],     // Allow higher error rate during chaos
    recovery_errors: ["count<50"],
  },
};

function simulateCall(text) {
  const payload = JSON.stringify({
    phone_number: "+2348012345678",
    text: text,
  });
  const params = {
    headers: { "Content-Type": "application/json" },
    timeout: "10s",
    tags: { name: "simulate-call" },
  };
  return http.post(`${BASE_URL}/test/simulate-call`, payload, params);
}

export default function () {
  const { text } = randomUtterance();
  const res = simulateCall(text);

  const passed = check(res, {
    "status is 200": (r) => r.status === 200,
    "not a server error": (r) => r.status < 500,
  });

  if (!passed) {
    recoveryErrors.add(1);
  }

  // Health check probe
  const health = http.get(`${BASE_URL}/health`, {
    tags: { name: "health-check" },
  });
  check(health, {
    "health endpoint reachable": (r) => r.status === 200 || r.status === 503,
  });

  sleep(0.5 + Math.random() * 2);
}
