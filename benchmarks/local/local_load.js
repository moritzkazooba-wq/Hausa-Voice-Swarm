/**
 * Local load test: ramp 1→10 sessions over 5 minutes with 3-turn conversations.
 *
 * Exercises a realistic intent mix using the shared utterance corpus.
 * Run locally against docker-compose stack.
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { randomUtterance, utteranceForIntent, weightedIntent } from "../utterances.js";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

export const options = {
  stages: [
    { duration: "30s", target: 3 },
    { duration: "1m", target: 5 },
    { duration: "2m", target: 10 },
    { duration: "1m", target: 10 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_duration: ["p(95)<2000", "p(99)<3000"],
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
  // 3-turn conversation simulating a real user session
  const primaryIntent = weightedIntent();

  // Turn 1: initial query
  const turn1Text = utteranceForIntent(primaryIntent);
  const res1 = simulateCall(turn1Text);
  check(res1, {
    "turn 1 status 200": (r) => r.status === 200,
    "turn 1 has response": (r) => r.json() && r.json().response !== undefined,
  });
  sleep(1 + Math.random() * 2); // Simulate user think time

  // Turn 2: follow-up (same intent or clarification)
  const turn2Text = utteranceForIntent(primaryIntent);
  const res2 = simulateCall(turn2Text);
  check(res2, {
    "turn 2 status 200": (r) => r.status === 200,
  });
  sleep(1 + Math.random() * 2);

  // Turn 3: different intent (user asks something else)
  const { text: turn3Text } = randomUtterance();
  const res3 = simulateCall(turn3Text);
  check(res3, {
    "turn 3 status 200": (r) => r.status === 200,
  });
  sleep(1 + Math.random());
}
